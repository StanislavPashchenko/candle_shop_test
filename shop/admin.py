from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import Candle, Category, CategoryGroup, Collection, Order, OrderItem


class CategoryInline(admin.TabularInline):
    model = Category
    extra = 0
    fields = ('name', 'name_ru', 'order')
    ordering = ('order', 'name')

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
    list_display = ('display_name', 'code', 'order')
    search_fields = ('code', 'title_uk', 'title_ru')
    ordering = ('order', 'code')
    fieldsets = (
        (None, {
            'fields': ('code', 'title_uk', 'title_ru', 'description_uk', 'description_ru', 'order')
        }),
    )

    def display_name(self, obj):
        return obj.display_name()

    display_name.short_description = _('Название коллекции')

@admin.register(Candle)
class CandleAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'price', 'category', 'collection', 'order', 'is_hit', 'is_on_sale', 'discount_percent')
    #list_editable = ('price', 'category', 'order', 'is_hit', 'is_on_sale', 'discount_percent')
    list_filter = ('is_hit', 'is_on_sale', 'category', 'collection')
    search_fields = ('name', 'name_ru', 'category__name')
    ordering = ('order', '-id')
    fieldsets = (
        (None, {
            'fields': ('name', 'name_ru', 'description', 'description_ru')
        }),
        ('Catalog', {
            'fields': ('price', 'image', 'image2', 'image3', 'category', 'collection', 'order', 'is_hit', 'is_on_sale', 'discount_percent')
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

