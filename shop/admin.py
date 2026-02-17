from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.forms import ModelForm
from django.core.exceptions import ValidationError
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
)

class CandleCategoryInline(admin.TabularInline):
    model = CandleCategory
    extra = 1
    fields = ('category', 'order')
    ordering = ('order',)


class CategoryInline(admin.TabularInline):
    model = Category
    extra = 0
    fields = ('name', 'name_ru', 'order')
    ordering = ('order', 'name')


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

class CandleImageInline(admin.TabularInline):
    model = CandleImage
    extra = 0
    fields = ('image', 'order')


@admin.register(Candle)
class CandleAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'price', 'order')
    inlines = [CandleCategoryInline, CandleImageInline]

    list_filter = (
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

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('price', 'quantity')
    fields = ('candle', 'quantity', 'price')


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

