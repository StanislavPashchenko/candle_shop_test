from django.shortcuts import render, get_object_or_404
from django.utils import translation
from .models import Candle, Collection
from django.core.paginator import Paginator
from django.db.models import Q, Case, When, Value, IntegerField
from django.db.models.functions import Lower
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import json
import urllib.parse
import urllib.request
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def _telegram_send_message(text: str) -> bool:
    token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '') or ''
    chat_id = getattr(settings, 'TELEGRAM_CHAT_ID', '') or ''
    logger.info('Telegram: token present=%s, chat_id=%s', bool(token), chat_id)
    if not token or not chat_id:
        logger.warning('Telegram: missing token or chat_id')
        return False

    url = f'https://api.telegram.org/bot{token}/sendMessage'
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'HTML',
        'disable_web_page_preview': True,
    }

    data = urllib.parse.urlencode(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode('utf-8', errors='replace')
            ok = getattr(resp, 'status', 200) == 200
            if not ok:
                logger.error('Telegram sendMessage failed: status=%s body=%s', getattr(resp, 'status', '?'), body[:500])
            else:
                logger.info('Telegram message sent successfully')
            return ok
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8', errors='replace')[:500]
        logger.error('Telegram HTTPError: status=%s body=%s', e.code, error_body)
        return False
    except Exception:
        logger.exception('Telegram sendMessage exception')
        return False


def _telegram_format_order_message(order, items, total, lang: str) -> str:
    def esc(s):
        if s is None:
            return ''
        return (str(s)
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;'))

    lines = [
        f'🧾 <b>Новый заказ #{esc(order.id)}</b>' if lang == 'ru' else f'🧾 <b>Нове замовлення #{esc(order.id)}</b>',
        f'<b>Клиент:</b> {esc(order.full_name)}' if lang == 'ru' else f'<b>Клієнт:</b> {esc(order.full_name)}',
        f'<b>Телефон:</b> {esc(order.phone)}',
        f'<b>Email:</b> {esc(order.email)}',
        f'<b>Город:</b> {esc(order.city)}' if lang == 'ru' else f'<b>Місто:</b> {esc(order.city)}',
        f'<b>Отделение:</b> {esc(order.warehouse)}' if lang == 'ru' else f'<b>Відділення:</b> {esc(order.warehouse)}',
    ]

    if getattr(order, 'payment_method', ''):
        pm = str(order.payment_method)
        if lang == 'ru':
            pm_label = {
                'card': 'Оплата картой',
                'cod': 'Оплата наложенным платежом',
            }.get(pm, pm)
        else:
            pm_label = {
                'card': 'Оплата карткою',
                'cod': 'Оплата накладеним платежем',
            }.get(pm, pm)
        lines.append(f'<b>Оплата:</b> {esc(pm_label)}')

    lines.append('')
    lines.append('<b>Товары:</b>' if lang == 'ru' else '<b>Товари:</b>')
    for it in items:
        candle = it.get('candle')
        qty = it.get('qty')
        subtotal = it.get('subtotal')
        try:
            name = candle.display_name if not callable(getattr(candle, 'display_name', None)) else candle.display_name()
        except Exception:
            name = str(candle)
        lines.append(f'• {esc(name)} × {esc(qty)} — {esc(subtotal)}')

    lines.append('')
    lines.append((f'<b>Итого:</b> {esc(total)}' if lang == 'ru' else f'<b>Разом:</b> {esc(total)}'))

    if getattr(order, 'notes', None):
        lines.append('')
        lines.append((f'<b>Примечания:</b> {esc(order.notes)}' if lang == 'ru' else f'<b>Нотатки:</b> {esc(order.notes)}'))

    return '\n'.join(lines)


def home(request):
    # Prefer candles explicitly marked as hits; show up to 6 on the homepage.
    hits = list(Candle.objects.filter(is_hit=True).order_by('order', '-id')[:6])
    if len(hits) < 6:
        # fill remaining slots with other candles (exclude already included)
        exclude_ids = [c.pk for c in hits]
        fill_qs = Candle.objects.exclude(pk__in=exclude_ids).order_by('order', '-id')[:(6 - len(hits))]
        hits.extend(list(fill_qs))
    candles = hits
    
    # Get collections for mood section
    collections = Collection.objects.all().order_by('order', 'code')
    
    cart = request.session.get('cart', {})
    cart_count = sum(cart.values()) if isinstance(cart, dict) else 0
    lang = (translation.get_language() or 'uk')[:2]
    template = f'shop/home_{lang}.html'
    return render(request, template, {
        'candles': candles, 
        'cart_count': cart_count,
        'collections': collections
    })


def product_list(request):
    from .models import Category
    q = request.GET.get('q', '').strip()
    
    # Создаем базовый queryset с кастомной сортировкой
    # Приоритет: хит+скидка -> скидка -> хит -> остальные -> по дате добавления
    qs = Candle.objects.all().annotate(
        sort_priority=Case(
            When(is_hit=True, is_on_sale=True, then=Value(0)),
            When(is_hit=False, is_on_sale=True, then=Value(1)),
            When(is_hit=True, is_on_sale=False, then=Value(2)),
            default=Value(3),
            output_field=IntegerField(),
        )
    )
    
    # collection filter
    collection_code = request.GET.get('collection')
    if collection_code:
        try:
            qs = qs.filter(collection__code=collection_code)
        except Exception:
            pass
    
    if q:
        # Some DB backends (SQLite) have limited Unicode case-folding in SQL functions.
        # To be robust: try case-insensitive lookups, and also match a capitalized
        # variant (common for stored product names) using plain contains.
        q_cap = q.capitalize()
        qs = qs.filter(
            Q(name__icontains=q) | Q(name_ru__icontains=q)
            | Q(category__name__icontains=q) | Q(category__name_ru__icontains=q)
            | Q(description__icontains=q) | Q(description_ru__icontains=q)
            | Q(name__contains=q_cap) | Q(name_ru__contains=q_cap)
            | Q(category__name__contains=q_cap) | Q(category__name_ru__contains=q_cap)
            | Q(description__contains=q_cap) | Q(description_ru__contains=q_cap)
        )

    # category filter
    category_id = request.GET.get('category')
    if category_id:
        try:
            qs = qs.filter(category_id=int(category_id))
        except (ValueError, TypeError):
            pass

    # price range filters
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    try:
        if min_price:
            qs = qs.filter(price__gte=float(min_price))
        if max_price:
            qs = qs.filter(price__lte=float(max_price))
    except (ValueError, TypeError):
        pass

    # sorting
    sort = request.GET.get('sort')
    if sort == 'price_asc':
        qs = qs.order_by('price')
    elif sort == 'price_desc':
        qs = qs.order_by('-price')
    elif sort == 'name_asc':
        qs = qs.order_by('name')
    elif sort == 'name_desc':
        qs = qs.order_by('-name')
    else:
        # Применяем кастомную сортировку по умолчанию
        qs = qs.order_by('sort_priority', '-id')

    cart = request.session.get('cart', {})
    cart_count = sum(cart.values()) if isinstance(cart, dict) else 0
    # categories for UI
    categories = Category.objects.all().order_by('order', 'name')

    # Pagination: 20 items per page
    paginator = Paginator(qs, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # preserve other query params when building pagination links
    current_get = request.GET.copy()
    if 'page' in current_get:
        current_get.pop('page')
    querystring = current_get.urlencode()

    lang = (translation.get_language() or 'uk')[:2]
    template = f'shop/product_list_{lang}.html'
    return render(request, template, {
        'candles': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
        'query': q,
        'cart_count': cart_count,
        'categories': categories,
        'querystring': querystring,
    })


def product_detail(request, pk):
    candle = get_object_or_404(Candle, pk=pk)
    cart = request.session.get('cart', {})
    cart_count = sum(cart.values()) if isinstance(cart, dict) else 0
    lang = (translation.get_language() or 'uk')[:2]
    template = f'shop/product_detail_{lang}.html'
    return render(request, template, {'candle': candle, 'cart_count': cart_count})


@require_POST
def add_to_cart(request):
    try:
        data = json.loads(request.body.decode('utf-8'))
        pk = int(data.get('pk'))
        qty = int(data.get('qty', 1))
    except Exception:
        return JsonResponse({'ok': False, 'error': 'invalid payload'}, status=400)

    candle = get_object_or_404(Candle, pk=pk)
    cart = request.session.get('cart', {})
    cart = dict(cart)
    cart[str(pk)] = cart.get(str(pk), 0) + max(1, qty)
    request.session['cart'] = cart
    request.session.modified = True
    total_items = sum(cart.values())
    return JsonResponse({'ok': True, 'items': total_items})


def cart_view(request):
    cart = request.session.get('cart', {})
    items = []
    total = 0
    for pk_str, qty in (cart.items() if isinstance(cart, dict) else []):
        try:
            c = Candle.objects.get(pk=int(pk_str))
        except Candle.DoesNotExist:
            continue
        items.append({'candle': c, 'qty': qty, 'subtotal': c.price * qty})
        total += c.price * qty
    cart_count = sum(cart.values()) if isinstance(cart, dict) else 0
    lang = (translation.get_language() or 'uk')[:2]
    template = f'shop/cart_{lang}.html'
    return render(request, template, {'items': items, 'total': total, 'cart_count': cart_count})


@require_POST
def update_cart(request):
    try:
        data = json.loads(request.body.decode('utf-8'))
        pk = str(int(data.get('pk')))
        action = data.get('action')
        qty = int(data.get('qty', 1))
    except Exception:
        return JsonResponse({'ok': False, 'error': 'invalid payload'}, status=400)

    cart = dict(request.session.get('cart', {}))

    if action == 'inc':
        cart[pk] = cart.get(pk, 0) + 1
    elif action == 'dec':
        if cart.get(pk, 0) > 1:
            cart[pk] = cart.get(pk, 0) - 1
        else:
            cart.pop(pk, None)
    elif action == 'set':
        if qty > 0:
            cart[pk] = qty
        else:
            cart.pop(pk, None)
    elif action == 'remove':
        cart.pop(pk, None)
    else:
        return JsonResponse({'ok': False, 'error': 'unknown action'}, status=400)

    request.session['cart'] = cart
    request.session.modified = True

    # compute totals
    items_total = sum(cart.values())
    total = 0
    item_qty = cart.get(pk, 0)
    item_subtotal = '0'
    for k, v in cart.items():
        try:
            c = Candle.objects.get(pk=int(k))
            total += c.price * v
        except Candle.DoesNotExist:
            continue

    if item_qty:
        try:
            c = Candle.objects.get(pk=int(pk))
            item_subtotal = str(c.price * item_qty)
        except Candle.DoesNotExist:
            item_subtotal = '0'

    return JsonResponse({'ok': True, 'items': items_total, 'item_qty': item_qty, 'item_subtotal': item_subtotal, 'total': str(total)})


def checkout(request):
    from .forms import OrderForm
    from .models import Order, OrderItem
    
    cart = request.session.get('cart', {})
    cart_count = sum(cart.values()) if isinstance(cart, dict) else 0
    
    # Получаем товары из корзины
    items = []
    total = 0
    for pk_str, qty in (cart.items() if isinstance(cart, dict) else []):
        try:
            c = Candle.objects.get(pk=int(pk_str))
            items.append({'candle': c, 'qty': qty, 'subtotal': c.price * qty})
            total += c.price * qty
        except Candle.DoesNotExist:
            continue
    
    lang = (translation.get_language() or 'uk')[:2]

    def _apply_ru_placeholders(f):
        if lang == 'ru':
            try:
                f.fields['full_name'].widget.attrs['placeholder'] = 'ФИО'
            except Exception:
                pass
        return f
    
    if request.method == 'POST':
        form = _apply_ru_placeholders(OrderForm(request.POST))
        if form.is_valid() and items:
            order = form.save(commit=False)
            
            # Получаем warehouse из скрытого поля
            warehouse = request.POST.get('warehouse', '').strip()
            logger.info('Selected warehouse: %s', warehouse)
            if not warehouse:
                # Сообщение об ошибке на соответствующем языке
                error_msg = 'Пожалуйста, выберите отделение Нової Почти.' if lang == 'uk' else 'Пожалуйста, выберите отделение Новой Почты.'
                form.add_error(None, error_msg)
                template = f'shop/checkout_{lang}.html'
                return render(request, template, {
                    'form': form,
                    'items': items,
                    'total': total,
                    'cart_count': cart_count
                })
            
            order.warehouse = warehouse
            order.save()
            
            # Добавляем товары в заказ
            for item in items:
                OrderItem.objects.create(
                    order=order,
                    candle=item['candle'],
                    quantity=item['qty'],
                    price=item['candle'].price
                )
            
            # Очищаем корзину
            request.session['cart'] = {}
            request.session.modified = True

            try:
                logger.info('Preparing Telegram notification for order %s', order.id)
                msg_text = _telegram_format_order_message(order, items, total, lang)
                logger.info('Telegram message text prepared, length=%s', len(msg_text))
                result = _telegram_send_message(msg_text)
                logger.info('Telegram send result: %s', result)
            except Exception:
                logger.exception('Error sending Telegram notification for order %s', order.id)

            # Редирект на страницу успеха
            return render(request, f'shop/order_success_{lang}.html', {'order': order, 'cart_count': 0})
        else:
            template = f'shop/checkout_{lang}.html'
            return render(request, template, {
                'form': form,
                'items': items,
                'total': total,
                'cart_count': cart_count
            })
    else:
        form = _apply_ru_placeholders(OrderForm())
    
    template = f'shop/checkout_{lang}.html'
    return render(request, template, {
        'form': form,
        'items': items,
        'total': total,
        'cart_count': cart_count
    })


def get_nova_poshta_warehouses(request):
    """Возвращает список отделений Новой Почты для города"""
    import requests
    
    city = request.GET.get('city', '').strip()
    if not city:
        return JsonResponse({'warehouses': []})

    try:
        # API Новой Почты
        url = 'https://api.novaposhta.ua/v2.0/json/'
        payload = {
            'apiKey': 'your_api_key_here',  # Неходится API ключ на сайте Новой Почты
            'modelName': 'AddressGeneral',
            'calledMethod': 'searchSettlements',
            'methodProperties': {
                'CityName': city,
                'Limit': 50
            }
        }
        
        response = requests.post(url, json=payload)
        data = response.json()
        
        if data.get('success') and data.get('data'):
            settlements = data['data'][0].get('Addresses', [])
            
            # Теперь получаем отделения для выбранного города
            if settlements:
                settlement_ref = settlements[0]['DeliveryCity']
                
                payload2 = {
                    'apiKey': 'your_api_key_here',
                    'modelName': 'AddressGeneral',
                    'calledMethod': 'getWarehouses',
                    'methodProperties': {
                        'CityRef': settlement_ref,
                        'Limit': 200
                    }
                }
                
                response2 = requests.post(url, json=payload2)
                data2 = response2.json()
                
                if data2.get('success') and data2.get('data'):
                    warehouses = [
                        {
                            'id': w['Ref'],
                            'name': w['Description']
                        }
                        for w in data2['data']
                    ]
                    return JsonResponse({'warehouses': warehouses})
    except Exception as e:
        print(f'Error: {e}')
    
    return JsonResponse({'warehouses': []})


def privacy_policy(request):
    cart = request.session.get('cart', {})
    cart_count = sum(cart.values()) if isinstance(cart, dict) else 0
    lang = (translation.get_language() or 'uk')[:2]
    template = f'shop/privacy_{lang}.html'
    contact_email = ''
    return render(request, template, {'cart_count': cart_count, 'contact_email': contact_email})
