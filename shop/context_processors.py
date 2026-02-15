from .models import Category, CategoryGroup

def categories(request):
    """Context processor to add all categories to every template"""
    return {
        'all_categories': Category.objects.select_related('group').all().order_by('group__order', 'group__name', 'order', 'name'),
        'all_category_groups': CategoryGroup.objects.prefetch_related('categories').all().order_by('order', 'name'),
    }
