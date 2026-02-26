def get_collection_detail_data(collection):
    items = (
        collection.items.select_related("candle")
        .prefetch_related("candle__options")
        .order_by("order", "id")[:6]
    )

    items_with_options_ids = []
    for item in items:
        if item.candle.options.exists():
            items_with_options_ids.append(item.candle.pk)

    return {
        "collection": collection,
        "items": items,
        "items_with_options_ids": items_with_options_ids,
    }
