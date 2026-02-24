from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.forms import ModelForm
from django.core.exceptions import ValidationError

try:
    import nested_admin
except Exception:
    nested_admin = None
from .models import (
    Candle,
    Category,
    CategoryGroup,
    CandleCategory,
    CandleImage,
    Collection,
    CollectionItem,
    Order,
    OrderItem,
    ProductOption,
    ProductOptionValue,
    OrderItemOption,
    Scent,
    ScentCategory,
    ScentCategoryLink,
)

_NestedTabularInline = nested_admin.NestedTabularInline if nested_admin else admin.TabularInline
_NestedModelAdmin = nested_admin.NestedModelAdmin if nested_admin else admin.ModelAdmin

class CandleCategoryInline(_NestedTabularInline):
    model = CandleCategory
    extra = 1
    fields = ('category', 'order')
    ordering = ('order',)


class CategoryInline(admin.TabularInline):
    model = Category
    extra = 0
    fields = ('name', 'name_ru', 'order')
    ordering = ('order', 'name')


class ScentCategoryInline(_NestedTabularInline):
    model = ScentCategoryLink
    extra = 1
    fields = ('category', 'order')
    ordering = ('order',)


class CollectionItemInlineForm(ModelForm):
    """Форма для товара в коллекции с валидацией максимума 5 штук."""
    
    def clean(self):
        cleaned_data = super().clean()
        collection = cleaned_data.get('collection')
        
        # Проверяем количество товаров в коллекции при создании нового
        # Только для уже сохранённых коллекций (при создании коллекции проверка отключается)
        if collection and collection.pk and not self.instance.pk:
            current_count = collection.items.count()
            if current_count >= 6:
                raise ValidationError(
                    f'В коллекции "{collection.display_name()}" уже максимальное количество товаров (6). '
                    f'Удалите один товар, чтобы добавить новый.'
                )
        
        return cleaned_data


class CollectionItemInline(admin.TabularInline):
    model = CollectionItem
    form = CollectionItemInlineForm
    extra = 0
    fields = ('candle', 'order')
    ordering = ('order', 'id')
    max_num = 6
    
    def get_extra(self, request, obj=None, **kwargs):
        """Уменьшаем extra если уже есть товары."""
        if obj and obj.pk:
            count = obj.items.count()
            return max(0, 6 - count)
        return 0

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'name_ru', 'group', 'order')
    search_fields = ('name', 'name_ru')
    fieldsets = (
        (None, {'fields': ('group', 'name', 'name_ru', 'description', 'order')}),
    )
    def display_name(self, obj):
        return obj.display_name()
    display_name.short_description = _('Название')


@admin.register(CategoryGroup)
class CategoryGroupAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'name_ru', 'order')
    search_fields = ('name', 'name_ru')
    ordering = ('order', 'name')
    fieldsets = (
        (None, {'fields': ('name', 'name_ru', 'order')}),
    )
    inlines = [CategoryInline]

    def display_name(self, obj):
        return obj.display_name()

    display_name.short_description = _('Название группы')


@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'code', 'order', 'items_count')
    search_fields = ('code', 'title_uk', 'title_ru')
    ordering = ('order', 'code')
    inlines = [CollectionItemInline]
    fieldsets = (
        (None, {
            'fields': ('code', 'title_uk', 'title_ru', 'description_uk', 'description_ru', 'banner', 'order')
        }),
    )

    def display_name(self, obj):
        return obj.display_name()

    display_name.short_description = _('Название коллекции')
    
    def items_count(self, obj):
        count = obj.items.count()
        return f'{count}/6'
    items_count.short_description = _('Товаров')


class CandleImageInline(_NestedTabularInline):
    model = CandleImage
    extra = 0
    fields = ('image', 'order')


# ========== INLINE ФОРМЫ ДЛЯ КОНФИГУРАТОРА ТОВАРОВ ==========


class ProductOptionValueInline(_NestedTabularInline):
    """Значения опции — редактируются внутри опции."""
    model = ProductOptionValue
    extra = 1
    fields = ('value', 'value_ru', 'image', 'price_modifier', 'sort_order')
    ordering = ('sort_order', 'id')


class ProductOptionInline(_NestedTabularInline):
    """Опции товара — редактируются прямо в карточке товара."""
    model = ProductOption
    extra = 1
    fields = ('name', 'name_ru', 'is_required', 'input_type', 'sort_order')
    ordering = ('sort_order', 'id')
    show_change_link = True
    if nested_admin:
        inlines = [ProductOptionValueInline]


@admin.register(Candle)
class CandleAdmin(_NestedModelAdmin):
    list_display = ('display_name', 'price', 'is_available', 'order')
    inlines = [CandleCategoryInline, CandleImageInline, ProductOptionInline]

    list_filter = (
        'is_available',
        'is_hit',
        'is_on_sale',
    )

    search_fields = (
        'name',
        'name_ru',
        'categories__name',
        'categories__name_ru',
    )

    ordering = ('order', '-id')

    fieldsets = (
        (None, {
            'fields': ('name', 'name_ru', 'description', 'description_ru')
        }),
        ('Catalog', {
            'fields': (
                'price',
                'is_available',
                'image',
                'image2',
                'image3',
                'order',
                'is_hit',
                'is_on_sale',
                'discount_percent',
            )
        }),
    )

    def display_name(self, obj):
        return obj.display_name()

    display_name.short_description = _('Название')


# ========== ADMIN КОНФИГУРАТОРА ТОВАРОВ ==========
# Примечание: ProductOption и ProductOptionValue управляются только через inline в CandleAdmin
# Отдельные админки убраны с боковой панели для упрощения


class OrderItemOptionInline(admin.TabularInline):
    """Отображение выбранных опций в позиции заказа."""
    model = OrderItemOption
    extra = 0
    readonly_fields = ('option_name', 'value_name', 'price_modifier')
    fields = ('option_name', 'value_name', 'price_modifier')


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('price', 'quantity', 'get_options_display')
    fields = ('candle', 'quantity', 'price', 'get_options_display')

    def get_options_display(self, obj):
        """Отображает выбранные опции для позиции."""
        opts = obj.selected_options.all()
        if not opts:
            return '-'
        return ', '.join([f'{o.option_name}: {o.value_name}' for o in opts])
    get_options_display.short_description = 'Выбранные опции'


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'full_name', 'phone', 'city', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('full_name', 'phone', 'email', 'city')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')
    inlines = [OrderItemInline]
    fieldsets = (
        ('Контактні дані', {
            'fields': ('full_name', 'phone', 'email')
        }),
        ('Доставка', {
            'fields': ('city', 'warehouse')
        }),
        ('Інші дані', {
            'fields': ('payment_method', 'notes', 'agree_to_terms', 'status')
        }),
        ('Дати', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Scent)
class ScentAdmin(_NestedModelAdmin):
    list_display = ('display_name', 'name_ru', 'order')
    list_filter = ('categories',)
    search_fields = ('name', 'name_ru')
    ordering = ('order', 'name')
    inlines = [ScentCategoryInline]
    fieldsets = (
        (None, {'fields': ('name', 'name_ru', 'description', 'description_ru', 'image', 'order')}),
    )

    def display_name(self, obj):
        return obj.display_name()
    display_name.short_description = _('Название аромата')


@admin.register(ScentCategory)
class ScentCategoryAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'name_ru', 'group', 'order')
    search_fields = ('name', 'name_ru')
    ordering = ('order', 'name')
    fieldsets = (
        (None, {'fields': ('group', 'name', 'name_ru', 'order')}),
    )

    def display_name(self, obj):
        return obj.display_name()
    display_name.short_description = _('Название категории')



