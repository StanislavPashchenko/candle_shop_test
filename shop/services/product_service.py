from django.core.paginator import Paginator
from django.db.models import Q, Case, When, Value, IntegerField

from ..models import Candle, Collection, HomeBanner, Category


def get_home_data():
    hits = list(Candle.objects.filter(is_hit=True).order_by("order", "-id")[:6])
    if len(hits) < 6:
        exclude_ids = [c.pk for c in hits]
        fill_qs = Candle.objects.exclude(pk__in=exclude_ids).order_by("order", "-id")[
            : (6 - len(hits))
        ]
        hits.extend(list(fill_qs))
    candles = hits

    candles_with_options_ids = []
    for c in Candle.objects.filter(pk__in=[c.pk for c in candles]).prefetch_related(
        "options"
    ):
        if c.options.exists():
            candles_with_options_ids.append(c.pk)

    collections = Collection.objects.all().order_by("order", "code")

    banners = list(HomeBanner.objects.filter(is_active=True).order_by("order", "-updated_at", "-id"))
    if not banners:
        banners = list(HomeBanner.objects.order_by("order", "-updated_at", "-id"))
    banners = [b for b in banners if getattr(b, "media", None)]

    return {
        "candles": candles,
        "collections": collections,
        "candles_with_options_ids": candles_with_options_ids,
        "banners": banners,
    }


def get_product_list_data(request):
    q = request.GET.get("q", "").strip()
    qs = (
        Candle.objects.prefetch_related("categories", "categories__group").annotate(
            sort_priority=Case(
                When(is_hit=True, is_on_sale=True, then=Value(0)),
                When(is_hit=False, is_on_sale=True, then=Value(1)),
                When(is_hit=True, is_on_sale=False, then=Value(2)),
                default=Value(3),
                output_field=IntegerField(),
            )
        )
    )

    collection_code = request.GET.get("collection")
    if collection_code:
        try:
            qs = qs.filter(collection__code=collection_code)
        except Exception:
            pass

    if q:
        q_cap = q.capitalize()
        qs = qs.filter(
            Q(name__icontains=q)
            | Q(name_ru__icontains=q)
            | Q(categories__name__icontains=q)
            | Q(categories__name_ru__icontains=q)
            | Q(description__icontains=q)
            | Q(description_ru__icontains=q)
            | Q(name__contains=q_cap)
            | Q(name_ru__contains=q_cap)
            | Q(categories__name__contains=q_cap)
            | Q(categories__name_ru__contains=q_cap)
            | Q(description__contains=q_cap)
            | Q(description_ru__contains=q_cap)
        ).distinct()

    category_id = request.GET.get("category")
    if category_id:
        try:
            qs = qs.filter(categories__id=int(category_id)).distinct()
        except (ValueError, TypeError):
            pass

    group_id = request.GET.get("group")
    if group_id:
        try:
            qs = qs.filter(categories__group_id=int(group_id)).distinct()
        except (ValueError, TypeError):
            pass

    min_price = request.GET.get("min_price")
    max_price = request.GET.get("max_price")
    try:
        if min_price:
            qs = qs.filter(price__gte=float(min_price))
        if max_price:
            qs = qs.filter(price__lte=float(max_price))
    except (ValueError, TypeError):
        pass

    sort = request.GET.get("sort")
    if sort == "price_asc":
        qs = qs.order_by("price")
    elif sort == "price_desc":
        qs = qs.order_by("-price")
    elif sort == "name_asc":
        qs = qs.order_by("name")
    elif sort == "name_desc":
        qs = qs.order_by("-name")
    else:
        qs = qs.order_by("sort_priority", "-id")

    categories = (
        Category.objects.select_related("group")
        .all()
        .order_by("group__order", "group__name", "order", "name")
    )

    paginator = Paginator(qs, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    candles_with_options_ids = []
    for c in page_obj:
        if c.options.exists():
            candles_with_options_ids.append(c.pk)

    current_get = request.GET.copy()
    if "page" in current_get:
        current_get.pop("page")
    querystring = current_get.urlencode()

    return {
        "candles": page_obj,
        "page_obj": page_obj,
        "paginator": paginator,
        "query": q,
        "categories": categories,
        "querystring": querystring,
        "candles_with_options_ids": candles_with_options_ids,
    }


def get_product_detail_data(candle):
    images = []
    seen = set()

    def add_url(u: str):
        if not u:
            return
        if u in seen:
            return
        seen.add(u)
        images.append(u)

    try:
        if candle.image and candle.image.url:
            add_url(candle.image.url)
    except Exception:
        pass
    try:
        if getattr(candle, "image2", None) and candle.image2 and candle.image2.url:
            add_url(candle.image2.url)
    except Exception:
        pass
    try:
        if getattr(candle, "image3", None) and candle.image3 and candle.image3.url:
            add_url(candle.image3.url)
    except Exception:
        pass

    try:
        for img in candle.images.all():
            try:
                if img.image and img.image.url:
                    add_url(img.image.url)
            except Exception:
                continue
    except Exception:
        pass

    product_options = candle.options.prefetch_related("values").order_by("sort_order", "id")

    options_data = []
    for option in product_options:
        option_data = {
            "id": option.id,
            "name": option.display_name(),
            "is_required": option.is_required,
            "is_required_effective": bool(option.is_required),
            "input_type": option.input_type,
            "values": [
                {
                    "id": val.id,
                    "value": val.display_value(),
                    "price_modifier": str(val.price_modifier),
                    "image_url": (val.image.url if getattr(val, "image", None) else ""),
                }
                for val in option.values.all().order_by("sort_order", "id")
            ],
        }
        options_data.append(option_data)

    return {
        "images": images,
        "options_data": options_data,
        "has_options": bool(options_data),
    }
