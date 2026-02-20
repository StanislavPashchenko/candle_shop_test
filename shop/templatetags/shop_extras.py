from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """
    Возвращает значение из словаря по ключу.
    Использование: {{ mydict|get_item:key_variable }}
    """
    if dictionary is None:
        return None
    return dictionary.get(key)
