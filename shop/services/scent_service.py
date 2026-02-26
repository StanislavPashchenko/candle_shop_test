from django.db.models import Prefetch

from ..models import Scent, ScentCategory, ScentCategoryGroup


def get_scent_list_data(request):
    scents = Scent.objects.all().order_by("order", "name")
    category_id = request.GET.get("category")
    if category_id:
        try:
            scents = scents.filter(categories__id=int(category_id)).distinct()
        except (ValueError, TypeError):
            pass

    scent_categories = ScentCategory.objects.all().order_by("order", "name")
    scent_category_groups = (
        ScentCategoryGroup.objects.prefetch_related(
            Prefetch("categories", queryset=ScentCategory.objects.order_by("order", "name"))
        )
        .all()
        .order_by("order", "name")
    )
    scent_categories_ungrouped = ScentCategory.objects.filter(group__isnull=True).order_by(
        "order", "name"
    )

    return {
        "scents": scents,
        "scent_categories": scent_categories,
        "scent_category_groups": scent_category_groups,
        "scent_categories_ungrouped": scent_categories_ungrouped,
    }


def get_scent_detail_data(scent):
    return {"scent": scent}
