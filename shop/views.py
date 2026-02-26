import json
import logging

from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import translation
from django.views.decorators.http import require_POST

from .models import Candle, Collection, Scent
from .services.cart_service import (
    add_to_cart as add_to_cart_item,
    build_cart_items,
    get_cart_count,
    update_cart as update_cart_item,
)
from .services.collection_service import get_collection_detail_data
from .services.delivery_service import get_nova_poshta_warehouses as fetch_nova_poshta_warehouses
from .services.order_service import create_order_with_items
from .services.product_service import (
    get_home_data,
    get_product_detail_data,
    get_product_list_data,
)
from .services.scent_service import get_scent_detail_data, get_scent_list_data
from .services.telegram_service import (
    telegram_format_order_message,
    telegram_send_message,
)

logger = logging.getLogger(__name__)


def home(request):
    cart = request.session.get('cart', {})
    cart_count = get_cart_count(cart)
    data = get_home_data()
    lang = (translation.get_language() or 'uk')[:2]
    template = f'shop/home_{lang}.html'
    return render(request, template, {
        **data,
        'cart_count': cart_count,
    })


def product_list(request):
    cart = request.session.get('cart', {})
    cart_count = get_cart_count(cart)
    data = get_product_list_data(request)
    lang = (translation.get_language() or 'uk')[:2]
    template = f'shop/product_list_{lang}.html'
    return render(request, template, {
        **data,
        'cart_count': cart_count,
    })


def product_detail(request, pk):
    candle = get_object_or_404(Candle, pk=pk)
    cart = request.session.get('cart', {})
    cart_count = get_cart_count(cart)
    data = get_product_detail_data(candle)
    lang = (translation.get_language() or 'uk')[:2]
    template = f'shop/product_detail_{lang}.html'
    return render(request, template, {
        'candle': candle,
        **data,
        'cart_count': cart_count,
    })


@require_POST
def add_to_cart(request):
    try:
        data = json.loads(request.body.decode('utf-8'))
        pk = int(data.get('pk'))
        qty = int(data.get('qty', 1))
        selected_options = data.get('options', {})  # {option_id: value_id, ...}
    except Exception as e:
        return JsonResponse({'ok': False, 'error': 'invalid payload'}, status=400)

    candle = get_object_or_404(Candle, pk=pk)

    if not candle.is_available:
        return JsonResponse({
            'ok': False,
            'error': 'out_of_stock',
            'message': 'Товара нет в наличии'
        }, status=400)

    cart = request.session.get('cart', {})
    cart, response, status = add_to_cart_item(cart, candle, qty, selected_options)
    if not response.get('ok'):
        return JsonResponse(response, status=status)

    request.session['cart'] = cart
    request.session.modified = True
    return JsonResponse(response, status=status)


def cart_view(request):
    cart = request.session.get('cart', {})
    items, total = build_cart_items(cart)
    cart_count = get_cart_count(cart)

    lang = (translation.get_language() or 'uk')[:2]
    template = f'shop/cart_{lang}.html'
    return render(request, template, {'items': items, 'total': total, 'cart_count': cart_count})


@require_POST
def update_cart(request):
    try:
        data = json.loads(request.body.decode('utf-8'))
        cart_key = str(data.get('pk'))  # Теперь pk — это cart_key
        action = data.get('action')
        qty = int(data.get('qty', 1))
    except Exception:
        return JsonResponse({'ok': False, 'error': 'invalid payload'}, status=400)

    cart = request.session.get('cart', {})
    cart, response, status = update_cart_item(cart, cart_key, action, qty)
    if response.get('ok'):
        request.session['cart'] = cart
        request.session.modified = True

    return JsonResponse(response, status=status)


def checkout(request):
    from .forms import OrderForm

    cart = request.session.get('cart', {})
    cart_count = get_cart_count(cart)
    items, total = build_cart_items(cart)

    lang = (translation.get_language() or 'uk')[:2]

    def apply_ru_placeholders(f):
        if lang == 'ru':
            try:
                f.fields['full_name'].widget.attrs['placeholder'] = 'ФИО'
            except Exception:
                pass
        return f

    if request.method == 'POST':
        form = apply_ru_placeholders(OrderForm(request.POST))
        if form.is_valid() and items:
            warehouse = request.POST.get('warehouse', '').strip()
            logger.info('Selected warehouse: %s', warehouse)
            if not warehouse:
                error_msg = 'Пожалуйста, выберите отделение Нової Почти.' if lang == 'uk' else 'Пожалуйста, выберите отделение Новой Почты.'
                form.add_error(None, error_msg)
                template = f'shop/checkout_{lang}.html'
                return render(request, template, {
                    'form': form,
                    'items': items,
                    'total': total,
                    'cart_count': cart_count
                })

            order = create_order_with_items(form, items, warehouse)
            request.session['cart'] = {}
            request.session.modified = True

            try:
                logger.info('Preparing Telegram notification for order %s', order.id)
                msg_text = telegram_format_order_message(order, items, total, lang)
                logger.info('Telegram message text prepared, length=%s', len(msg_text))
                result = telegram_send_message(msg_text)
                logger.info('Telegram send result: %s', result)
            except Exception:
                logger.exception('Error sending Telegram notification for order %s', order.id)

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
        form = apply_ru_placeholders(OrderForm())

    template = f'shop/checkout_{lang}.html'
    return render(request, template, {
        'form': form,
        'items': items,
        'total': total,
        'cart_count': cart_count
    })


def get_nova_poshta_warehouses(request):
    city = request.GET.get('city', '').strip()
    warehouses = fetch_nova_poshta_warehouses(city)
    return JsonResponse({'warehouses': warehouses})


def privacy_policy(request):
    cart = request.session.get('cart', {})
    cart_count = get_cart_count(cart)
    lang = (translation.get_language() or 'uk')[:2]
    template = f'shop/privacy_{lang}.html'
    contact_email = ''
    return render(request, template, {'cart_count': cart_count, 'contact_email': contact_email})


def collection_detail(request, code):
    collection = get_object_or_404(Collection, code=code)
    data = get_collection_detail_data(collection)
    cart = request.session.get('cart', {})
    cart_count = get_cart_count(cart)

    lang = translation.get_language() or 'uk'
    if lang.startswith('ru'):
        template = 'shop/mood_collection_ru.html'
    else:
        template = 'shop/mood_collection_uk.html'

    return render(request, template, {
        **data,
        'cart_count': cart_count,
    })


def scent_list(request):
    cart = request.session.get('cart', {})
    cart_count = get_cart_count(cart)
    data = get_scent_list_data(request)
    lang = (translation.get_language() or 'uk')[:2]
    template = f'shop/scent_{lang}.html'
    return render(request, template, {
        **data,
        'cart_count': cart_count,
    })


def scent_detail(request, pk: int):
    scent = get_object_or_404(Scent, pk=pk)

    cart = request.session.get('cart', {})
    cart_count = get_cart_count(cart)
    data = get_scent_detail_data(scent)

    lang = (translation.get_language() or 'uk')[:2]
    template = f'shop/scent_detail_{lang}.html'
    return render(request, template, {
        **data,
        'cart_count': cart_count,
    })
