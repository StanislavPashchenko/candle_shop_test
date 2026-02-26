from ..models import OrderItem, OrderItemOption, ProductOption, ProductOptionValue


def create_order_with_items(form, items, warehouse: str):
    order = form.save(commit=False)
    order.warehouse = warehouse
    order.save()

    for item in items:
        order_item = OrderItem.objects.create(
            order=order,
            candle=item["candle"],
            quantity=item["qty"],
            price=item["price"],
        )

        for opt_id, val_id in item["selected_options"].items():
            try:
                option = ProductOption.objects.get(id=int(opt_id))
                value = ProductOptionValue.objects.get(id=int(val_id))
                if val_id:
                    OrderItemOption.objects.create(
                        order_item=order_item,
                        option_name=option.display_name(),
                        value_name=value.display_value(),
                        price_modifier=value.price_modifier,
                    )
            except (ProductOption.DoesNotExist, ProductOptionValue.DoesNotExist):
                pass

    return order
