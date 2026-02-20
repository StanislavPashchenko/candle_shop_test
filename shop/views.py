from django.shortcuts import render, get_object_or_404
from django.utils import translation
from .models import Candle, Collection, CollectionItem, ProductOption, ProductOptionValue, OrderItemOption
from django.core.paginator import Paginator
from django.db.models import Q, Case, When, Value, IntegerField
from django.db.models.functions import Lower
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from decimal import Decimal
import json
import urllib.parse
import urllib.request
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def _get_cart_count(cart) -> int:
    if not isinstance(cart, dict):
        return 0
    total = 0
    for v in cart.values():
        if isinstance(v, dict):
            try:
                total += int(v.get('qty', 0) or 0)
            except Exception:
                continue
        else:
            try:
                total += int(v or 0)
            except Exception:
                continue
    return total


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
        options_display = it.get('options_display', {})
        try:
            name = candle.display_name if not callable(getattr(candle, 'display_name', None)) else candle.display_name()
        except Exception:
            name = str(candle)

        # Основная строка товара
        lines.append(f'• {esc(name)} × {esc(qty)} — {esc(subtotal)}')

        # Добавляем опции, если есть
        if options_display:
            opts_str = ', '.join([f'{k}: {v}' for k, v in options_display.items()])
            lines.append(f'  └ {esc(opts_str)}')

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
    cart_count = _get_cart_count(cart)
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
    qs = (
        Candle.objects
        .prefetch_related('categories', 'categories__group')
        .annotate(
            sort_priority=Case(
                When(is_hit=True, is_on_sale=True, then=Value(0)),
                When(is_hit=False, is_on_sale=True, then=Value(1)),
                When(is_hit=True, is_on_sale=False, then=Value(2)),
                default=Value(3),
                output_field=IntegerField(),
            )
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
            | Q(categories__name__icontains=q) | Q(categories__name_ru__icontains=q)
            | Q(description__icontains=q) | Q(description_ru__icontains=q)
            | Q(name__contains=q_cap) | Q(name_ru__contains=q_cap)
            | Q(categories__name__contains=q_cap) | Q(categories__name_ru__contains=q_cap)
            | Q(description__contains=q_cap) | Q(description_ru__contains=q_cap)
        ).distinct()

    # category filter
    category_id = request.GET.get('category')
    if category_id:
        try:
            qs = qs.filter(categories__id=int(category_id)).distinct()
        except (ValueError, TypeError):
            pass

    # group filter
    group_id = request.GET.get('group')
    if group_id:
        try:
            qs = qs.filter(categories__group_id=int(group_id)).distinct()
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
    cart_count = _get_cart_count(cart)
    # categories for UI
    categories = Category.objects.select_related('group').all().order_by('group__order', 'group__name', 'order', 'name')

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
    images = []
    seen = set()

    def _add_url(u: str):
        if not u:
            return
        if u in seen:
            return
        seen.add(u)
        images.append(u)

    try:
        if candle.image and candle.image.url:
            _add_url(candle.image.url)
    except Exception:
        pass
    try:
        if getattr(candle, 'image2', None) and candle.image2 and candle.image2.url:
            _add_url(candle.image2.url)
    except Exception:
        pass
    try:
        if getattr(candle, 'image3', None) and candle.image3 and candle.image3.url:
            _add_url(candle.image3.url)
    except Exception:
        pass

    # Backward compatibility: if there are CandleImage records, include them too.
    try:
        for img in candle.images.all():
            try:
                if img.image and img.image.url:
                    _add_url(img.image.url)
            except Exception:
                continue
    except Exception:
        pass

    # Загружаем опции товара с prefetch_related для оптимизации
    product_options = (
        candle.options
        .prefetch_related('values')
        .order_by('sort_order', 'id')
    )

    # Формируем структурированные данные для фронтенда
    options_data = []
    for option in product_options:
        has_values = option.values.exists()
        option_data = {
            'id': option.id,
            'name': option.display_name(),
            'is_required': option.is_required,
            'is_required_effective': bool(option.is_required or has_values),
            'input_type': option.input_type,
            'values': [
                {
                    'id': val.id,
                    'value': val.display_value(),
                    'price_modifier': str(val.price_modifier)
                }
                for val in option.values.all().order_by('sort_order', 'id')
            ]
        }
        options_data.append(option_data)

    cart = request.session.get('cart', {})
    cart_count = _get_cart_count(cart)
    lang = (translation.get_language() or 'uk')[:2]
    template = f'shop/product_detail_{lang}.html'
    return render(request, template, {
        'candle': candle,
        'cart_count': cart_count,
        'images': images,
        'options_data': options_data,
        'has_options': bool(options_data)
    })


@require_POST
def add_to_cart(request):
    """
    Добавление товара в корзину с опциями конфигуратора.
    Ключ корзины: pk_optionId1:valueId1_optionId2:valueId2...
    """
    try:
        data = json.loads(request.body.decode('utf-8'))
        pk = int(data.get('pk'))
        qty = int(data.get('qty', 1))
        selected_options = data.get('options', {})  # {option_id: value_id, ...}
    except Exception as e:
        return JsonResponse({'ok': False, 'error': 'invalid payload'}, status=400)

    candle = get_object_or_404(Candle, pk=pk)

    # ===== СЕРВЕРНАЯ ВАЛИДАЦИЯ ОПЦИЙ =====
    # Загружаем все опции товара для проверки
    product_options = (
        ProductOption.objects
        .filter(product=candle)
        .prefetch_related('values')
    )

    # Проверяем обязательные опции.
    # Правило: если у опции есть значения, пользователь обязан выбрать одно значение,
    # даже если is_required=False.
    required_options = {
        opt.id: opt
        for opt in product_options
        if opt.is_required or opt.values.exists()
    }
    for req_id, req_opt in required_options.items():
        if str(req_id) not in selected_options or not selected_options[str(req_id)]:
            return JsonResponse({
                'ok': False,
                'error': 'missing_required_options',
                'message': f'Не выбрана обязательная опция: {req_opt.name}'
            }, status=400)

    # Проверяем, что выбранные значения принадлежат этому товару
    validated_options = {}
    total_price_modifier = 0

    for opt_id_str, val_id in selected_options.items():
        if not val_id:  # Пропускаем пустые значения необязательных опций
            continue

        try:
            opt_id = int(opt_id_str)
            val_id = int(val_id)
        except (ValueError, TypeError):
            return JsonResponse({
                'ok': False,
                'error': 'invalid_option_format',
                'message': 'Некорректный формат опций'
            }, status=400)

        # Проверяем, что опция принадлежит этому товару
        option = product_options.filter(id=opt_id).first()
        if not option:
            return JsonResponse({
                'ok': False,
                'error': 'invalid_option',
                'message': f'Опция {opt_id} не принадлежит данному товару'
            }, status=400)

        # Проверяем, что значение принадлежит этой опции
        value = option.values.filter(id=val_id).first()
        if not value:
            return JsonResponse({
                'ok': False,
                'error': 'invalid_value',
                'message': f'Значение {val_id} не принадлежит опции {option.name}'
            }, status=400)

        validated_options[opt_id] = {
            'option': option,
            'value': value,
            'option_name': option.display_name(),
            'value_name': value.display_value(),
            'price_modifier': value.price_modifier
        }
        total_price_modifier += value.price_modifier

    # Формируем уникальный ключ для корзины
    # pk_option1:value1_option2:value2
    option_parts = [f"{opt_id}:{val['value'].id}" for opt_id, val in sorted(validated_options.items())]
    cart_key = f"{pk}_{'_'.join(option_parts)}" if option_parts else str(pk)

    # Сохраняем в сессии
    cart = request.session.get('cart', {})
    cart = dict(cart)

    # Структура корзины: {cart_key: {'qty': N, 'options': {...}, 'price_modifier': X}}
    if cart_key not in cart:
        cart[cart_key] = {
            'pk': pk,
            'qty': 0,
            'options': {str(k): v['value'].id for k, v in validated_options.items()},
            'options_display': {v['option_name']: v['value_name'] for v in validated_options.values()},
            'price_modifier': str(total_price_modifier)
        }

    cart[cart_key]['qty'] += max(1, qty)
    request.session['cart'] = cart
    request.session.modified = True

    total_items = sum(item['qty'] if isinstance(item, dict) else item for item in cart.values())

    return JsonResponse({
        'ok': True,
        'items': total_items,
        'cart_key': cart_key,
        'final_price': str(candle.discounted_price() + total_price_modifier)
    })


def cart_view(request):
    """Отображение корзины с учетом опций товаров."""
    cart = request.session.get('cart', {})
    items = []
    total = 0

    for cart_key, cart_item in (cart.items() if isinstance(cart, dict) else []):
        # Определяем структуру: старая (просто qty) или новая (словарь)
        if isinstance(cart_item, dict):
            pk = cart_item.get('pk')
            qty = cart_item.get('qty', 1)
            price_modifier = Decimal(cart_item.get('price_modifier', '0') or '0')
            options_display = cart_item.get('options_display', {})
        else:
            # Обратная совместимость со старой структурой
            pk = cart_key
            qty = cart_item
            price_modifier = Decimal('0')
            options_display = {}
            cart_key = str(pk)

        try:
            candle = Candle.objects.get(pk=int(pk))
            final_price = candle.discounted_price() + price_modifier
            subtotal = final_price * qty

            items.append({
                'cart_key': cart_key,
                'candle': candle,
                'qty': qty,
                'price': final_price,
                'subtotal': subtotal,
                'options_display': options_display,
                'price_modifier': price_modifier
            })
            total += subtotal
        except Candle.DoesNotExist:
            continue

    cart_count = sum(
        item['qty'] if isinstance(item, dict) else item
        for item in cart.values()
    ) if isinstance(cart, dict) else 0

    lang = (translation.get_language() or 'uk')[:2]
    template = f'shop/cart_{lang}.html'
    return render(request, template, {'items': items, 'total': total, 'cart_count': cart_count})


@require_POST
def update_cart(request):
    """Обновление количества товара в корзине."""
    try:
        data = json.loads(request.body.decode('utf-8'))
        cart_key = str(data.get('pk'))  # Теперь pk — это cart_key
        action = data.get('action')
        qty = int(data.get('qty', 1))
    except Exception:
        return JsonResponse({'ok': False, 'error': 'invalid payload'}, status=400)

    cart = dict(request.session.get('cart', {}))

    if cart_key not in cart:
        return JsonResponse({'ok': False, 'error': 'item not found'}, status=404)

    cart_item = cart[cart_key]

    # Определяем структуру
    if isinstance(cart_item, dict):
        current_qty = cart_item.get('qty', 0)
    else:
        current_qty = cart_item

    if action == 'inc':
        new_qty = current_qty + 1
    elif action == 'dec':
        new_qty = current_qty - 1 if current_qty > 1 else 0
    elif action == 'set':
        new_qty = qty
    elif action == 'remove':
        new_qty = 0
    else:
        return JsonResponse({'ok': False, 'error': 'unknown action'}, status=400)

    if new_qty > 0:
        if isinstance(cart_item, dict):
            cart[cart_key]['qty'] = new_qty
        else:
            cart[cart_key] = new_qty
    else:
        cart.pop(cart_key, None)

    request.session['cart'] = cart
    request.session.modified = True

    # Подсчет итогов
    items_total = sum(
        item['qty'] if isinstance(item, dict) else item
        for item in cart.values()
    )

    total = Decimal('0')
    item_subtotal = Decimal('0')

    for key, item in cart.items():
        try:
            if isinstance(item, dict):
                pk = item.get('pk')
                item_qty = item.get('qty', 1)
                price_mod = Decimal(item.get('price_modifier', '0') or '0')
            else:
                pk = key
                item_qty = item
                price_mod = Decimal('0')

            c = Candle.objects.get(pk=int(pk))
            item_price = c.discounted_price() + price_mod

            if key == cart_key:
                item_subtotal = item_price * (new_qty if new_qty > 0 else 0)

            total += item_price * item_qty
        except Candle.DoesNotExist:
            continue

    return JsonResponse({
        'ok': True,
        'items': items_total,
        'item_qty': new_qty if new_qty > 0 else 0,
        'item_subtotal': str(item_subtotal),
        'total': str(total)
    })


def checkout(request):
    """Оформление заказа с сохранением выбранных опций товаров."""
    from .forms import OrderForm
    from .models import Order, OrderItem
    from decimal import Decimal

    cart = request.session.get('cart', {})
    cart_count = sum(
        item['qty'] if isinstance(item, dict) else item
        for item in cart.values()
    ) if isinstance(cart, dict) else 0

    # Получаем товары из корзины с опциями
    items = []
    total = Decimal('0')
    for cart_key, cart_item in (cart.items() if isinstance(cart, dict) else []):
        if isinstance(cart_item, dict):
            pk = cart_item.get('pk')
            qty = cart_item.get('qty', 1)
            price_modifier = Decimal(cart_item.get('price_modifier', '0') or '0')
            options_display = cart_item.get('options_display', {})
            selected_options = cart_item.get('options', {})
        else:
            # Обратная совместимость
            pk = cart_key
            qty = cart_item
            price_modifier = Decimal('0')
            options_display = {}
            selected_options = {}

        try:
            candle = Candle.objects.get(pk=int(pk))
            final_price = candle.discounted_price() + price_modifier
            subtotal = final_price * qty

            items.append({
                'cart_key': cart_key,
                'candle': candle,
                'qty': qty,
                'price': final_price,
                'subtotal': subtotal,
                'options_display': options_display,
                'selected_options': selected_options,
                'price_modifier': price_modifier
            })
            total += subtotal
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

            # Добавляем товары в заказ с опциями
            for item in items:
                order_item = OrderItem.objects.create(
                    order=order,
                    candle=item['candle'],
                    quantity=item['qty'],
                    price=item['price']
                )

                # Сохраняем выбранные опции
                for opt_id, val_id in item['selected_options'].items():
                    try:
                        option = ProductOption.objects.get(id=int(opt_id))
                        value = ProductOptionValue.objects.get(id=int(val_id))
                        OrderItemOption.objects.create(
                            order_item=order_item,
                            option_name=option.display_name(),
                            value_name=value.display_value(),
                            price_modifier=value.price_modifier
                        )
                    except (ProductOption.DoesNotExist, ProductOptionValue.DoesNotExist):
                        pass

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

    api_key = getattr(settings, 'NOVA_POSHTA_API_KEY', '')
    if not api_key:
        logger.warning('Nova Poshta API key not configured')
        return JsonResponse({'warehouses': []})

    try:
        # API Новой Почты
        url = 'https://api.novaposhta.ua/v2.0/json/'
        payload = {
            'apiKey': api_key,
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
                    'apiKey': api_key,
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
        logger.error(f'Nova Poshta API error: {e}')
    
    return JsonResponse({'warehouses': []})


def privacy_policy(request):
    cart = request.session.get('cart', {})
    cart_count = sum(
        item['qty'] if isinstance(item, dict) else item
        for item in cart.values()
    ) if isinstance(cart, dict) else 0
    lang = (translation.get_language() or 'uk')[:2]
    template = f'shop/privacy_{lang}.html'
    contact_email = ''
    return render(request, template, {'cart_count': cart_count, 'contact_email': contact_email})


def collection_detail(request, code):
    """Страница коллекции по настроению с до 6 товарами."""
    from django.utils import translation
    collection = get_object_or_404(Collection, code=code)

    # Получаем товары коллекции, отсортированные по order
    items = (collection.items
             .select_related('candle')
             .order_by('order', 'id')[:6])

    cart = request.session.get('cart', {})
    cart_count = sum(
        item['qty'] if isinstance(item, dict) else item
        for item in cart.values()
    ) if isinstance(cart, dict) else 0

    # Выбираем шаблон в зависимости от языка
    lang = translation.get_language() or 'uk'
    if lang.startswith('ru'):
        template = 'shop/mood_collection_ru.html'
    else:
        template = 'shop/mood_collection_uk.html'

    return render(request, template, {
        'collection': collection,
        'items': items,
        'cart_count': cart_count,
    })
