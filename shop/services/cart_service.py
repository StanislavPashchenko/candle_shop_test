from decimal import Decimal
from typing import Any, Dict, Tuple

from ..models import Candle, ProductOption


def get_cart_count(cart: Any) -> int:
    if not isinstance(cart, dict):
        return 0
    total = 0
    for v in cart.values():
        if isinstance(v, dict):
            try:
                total += int(v.get("qty", 0) or 0)
            except Exception:
                continue
        else:
            try:
                total += int(v or 0)
            except Exception:
                continue
    return total


def build_cart_items(cart: Any):
    items = []
    total = Decimal("0")
    for cart_key, cart_item in (cart.items() if isinstance(cart, dict) else []):
        if isinstance(cart_item, dict):
            pk = cart_item.get("pk")
            qty = cart_item.get("qty", 1)
            price_modifier = Decimal(cart_item.get("price_modifier", "0") or "0")
            options_display = cart_item.get("options_display", {})
            selected_options = cart_item.get("options", {})
        else:
            pk = cart_key
            qty = cart_item
            price_modifier = Decimal("0")
            options_display = {}
            selected_options = {}

        try:
            candle = Candle.objects.get(pk=int(pk))
            final_price = candle.discounted_price() + price_modifier
            subtotal = final_price * qty
            items.append(
                {
                    "cart_key": cart_key,
                    "candle": candle,
                    "qty": qty,
                    "price": final_price,
                    "subtotal": subtotal,
                    "options_display": options_display,
                    "selected_options": selected_options,
                    "price_modifier": price_modifier,
                }
            )
            total += subtotal
        except Candle.DoesNotExist:
            continue
    return items, total


def add_to_cart(cart: Any, candle, qty: int, selected_options: Dict[str, Any]):
    product_options = (
        ProductOption.objects.filter(product=candle).prefetch_related("values")
    )
    required_options = {opt.id: opt for opt in product_options if opt.is_required}
    for req_id, req_opt in required_options.items():
        if str(req_id) not in selected_options or not selected_options[str(req_id)]:
            return (
                cart,
                {
                    "ok": False,
                    "error": "missing_required_options",
                    "message": f"Не выбрана обязательная опция: {req_opt.name}",
                },
                400,
            )

    validated_options = {}
    total_price_modifier = Decimal("0")

    for opt_id_str, val_id in selected_options.items():
        if not val_id:
            continue

        try:
            opt_id = int(opt_id_str)
            val_id = int(val_id)
        except (ValueError, TypeError):
            return (
                cart,
                {
                    "ok": False,
                    "error": "invalid_option_format",
                    "message": "Некорректный формат опций",
                },
                400,
            )

        option = product_options.filter(id=opt_id).first()
        if not option:
            return (
                cart,
                {
                    "ok": False,
                    "error": "invalid_option",
                    "message": f"Опция {opt_id} не принадлежит данному товару",
                },
                400,
            )

        value = option.values.filter(id=val_id).first()
        if not value:
            return (
                cart,
                {
                    "ok": False,
                    "error": "invalid_value",
                    "message": f"Значение {val_id} не принадлежит опции {option.name}",
                },
                400,
            )

        validated_options[opt_id] = {
            "option": option,
            "value": value,
            "option_name": option.display_name(),
            "value_name": value.display_value(),
            "price_modifier": value.price_modifier,
        }
        total_price_modifier += value.price_modifier

    option_parts = [
        f"{opt_id}:{val['value'].id}" for opt_id, val in sorted(validated_options.items())
    ]
    cart_key = f"{candle.pk}_{'_'.join(option_parts)}" if option_parts else str(candle.pk)

    cart = dict(cart or {})
    if cart_key not in cart:
        cart[cart_key] = {
            "pk": candle.pk,
            "qty": 0,
            "options": {str(k): v["value"].id for k, v in validated_options.items()},
            "options_display": {
                v["option_name"]: v["value_name"] for v in validated_options.values()
            },
            "price_modifier": str(total_price_modifier),
        }

    cart[cart_key]["qty"] += max(1, qty)

    total_items = sum(
        item["qty"] if isinstance(item, dict) else item for item in cart.values()
    )

    return (
        cart,
        {
            "ok": True,
            "items": total_items,
            "cart_key": cart_key,
            "final_price": str(candle.discounted_price() + total_price_modifier),
        },
        200,
    )


def update_cart(cart: Any, cart_key: str, action: str, qty: int):
    cart = dict(cart or {})

    if cart_key not in cart:
        return cart, {"ok": False, "error": "item not found"}, 404

    cart_item = cart[cart_key]
    if isinstance(cart_item, dict):
        current_qty = cart_item.get("qty", 0)
    else:
        current_qty = cart_item

    if action == "inc":
        new_qty = current_qty + 1
    elif action == "dec":
        new_qty = current_qty - 1 if current_qty > 1 else 0
    elif action == "set":
        new_qty = qty
    elif action == "remove":
        new_qty = 0
    else:
        return cart, {"ok": False, "error": "unknown action"}, 400

    if new_qty > 0:
        if isinstance(cart_item, dict):
            cart[cart_key]["qty"] = new_qty
        else:
            cart[cart_key] = new_qty
    else:
        cart.pop(cart_key, None)

    items_total = sum(
        item["qty"] if isinstance(item, dict) else item for item in cart.values()
    )

    total = Decimal("0")
    item_subtotal = Decimal("0")

    for key, item in cart.items():
        try:
            if isinstance(item, dict):
                pk = item.get("pk")
                item_qty = item.get("qty", 1)
                price_mod = Decimal(item.get("price_modifier", "0") or "0")
            else:
                pk = key
                item_qty = item
                price_mod = Decimal("0")

            c = Candle.objects.get(pk=int(pk))
            item_price = c.discounted_price() + price_mod

            if key == cart_key:
                item_subtotal = item_price * (new_qty if new_qty > 0 else 0)

            total += item_price * item_qty
        except Candle.DoesNotExist:
            continue

    return (
        cart,
        {
            "ok": True,
            "items": items_total,
            "item_qty": new_qty if new_qty > 0 else 0,
            "item_subtotal": str(item_subtotal),
            "total": str(total),
        },
        200,
    )
