from django.db import models
from django.utils import translation


class CategoryGroup(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name='Название группы (укр)')
    name_ru = models.CharField(max_length=100, blank=True, null=True, verbose_name='Название группы (рус)')
    order = models.PositiveIntegerField(default=0, verbose_name='Порядок')

    class Meta:
        verbose_name_plural = 'Группы категорий'
        ordering = ['order', 'name']

    def __str__(self):
        return self.display_name()

    def display_name(self):
        lang = (translation.get_language() or '').lower()
        if lang.startswith('uk'):
            return self.name or self.name_ru or ''
        if lang.startswith('ru'):
            return self.name_ru or self.name or ''
        return self.name or self.name_ru or ''
    
class Category(models.Model):
    group = models.ForeignKey(
        CategoryGroup,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='categories',
        verbose_name='Группа',
    )
    name = models.CharField(max_length=100, verbose_name='Название (укр)')
    name_ru = models.CharField(max_length=100, blank=True, null=True, verbose_name='Название (рус)')
    description = models.TextField(blank=True, verbose_name='Описание')
    order = models.PositiveIntegerField(default=0, verbose_name='Порядок')

    class Meta:
        verbose_name_plural = 'Категории'
        ordering = ['group__order', 'group__name', 'order', 'name']
        constraints = [
            models.UniqueConstraint(fields=['group', 'name'], name='uniq_category_group_name_uk'),
        ]

    def __str__(self):
        return self.display_name()

    def display_name(self):
        lang = (translation.get_language() or '').lower()
        if lang.startswith('uk'):
            return self.name or self.name_ru or ''
        if lang.startswith('ru'):
            return self.name_ru or self.name or ''
        return self.name or self.name_ru or ''

class CandleCategory(models.Model):
    candle = models.ForeignKey(
        'Candle',
        on_delete=models.CASCADE,
        related_name='category_links'
    )
    category = models.ForeignKey(
        'Category',
        on_delete=models.CASCADE,
        related_name='candle_links'
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']
        unique_together = ('candle', 'category')



class Collection(models.Model):
    """Коллекции по настроению (Для релакса / Для подарка / Для дому и т.п.)."""

    code = models.SlugField(
        max_length=50,
        unique=True,
        verbose_name='Код (латиницей)',
        help_text='Технический код, например relax, gift, home.',
    )
    title_uk = models.CharField(max_length=120, verbose_name='Назва (укр)')
    title_ru = models.CharField(max_length=120, blank=True, null=True, verbose_name='Название (рус)')
    description_uk = models.TextField(blank=True, verbose_name='Опис (укр)')
    description_ru = models.TextField(blank=True, null=True, verbose_name='Описание (рус)')
    description = models.TextField(blank=True, verbose_name='Опис / Описание')
    banner = models.ImageField(upload_to='collections/', blank=True, null=True, verbose_name='Баннер коллекции')
    order = models.PositiveIntegerField(default=0, verbose_name='Порядок')

    class Meta:
        verbose_name = 'Коллекция по настроению'
        verbose_name_plural = 'Коллекции по настроению'
        ordering = ['order', 'code']

    def __str__(self):
        return self.display_name()

    def display_name(self):
        lang = (translation.get_language() or '').lower()
        if lang.startswith('uk'):
            return self.title_uk or self.title_ru or ''
        if lang.startswith('ru'):
            return self.title_ru or self.title_uk or ''
        return self.title_uk or self.title_ru or ''

    def display_description(self):
        lang = (translation.get_language() or '').lower()
        if lang.startswith('uk'):
            return self.description_uk or self.description_ru or self.description or ''
        if lang.startswith('ru'):
            return self.description_ru or self.description_uk or self.description or ''
        return self.description_uk or self.description_ru or self.description or ''


class CollectionItem(models.Model):
    """Товары в коллекции (до 5 штук с сортировкой)."""

    collection = models.ForeignKey(
        Collection,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Коллекция'
    )
    candle = models.ForeignKey(
        'Candle',
        on_delete=models.CASCADE,
        related_name='collection_items',
        verbose_name='Свеча'
    )
    order = models.PositiveIntegerField(default=0, verbose_name='Порядок')

    class Meta:
        verbose_name = 'Товар в коллекции'
        verbose_name_plural = 'Товары в коллекции'
        ordering = ['order', 'id']
        constraints = [
            models.UniqueConstraint(fields=['collection', 'candle'], name='uniq_collection_candle'),
        ]

    def __str__(self):
        return f'{self.collection.display_name()} — {self.candle.display_name()}'


class Candle(models.Model):
    name = models.CharField(max_length=200, verbose_name='Название (укр)')
    name_ru = models.CharField(max_length=200, blank=True, null=True, verbose_name='Название (рус)')
    description = models.TextField(verbose_name='Описание (укр)')
    description_ru = models.TextField(blank=True, null=True, verbose_name='Описание (рус)')
    price = models.DecimalField(max_digits=8, decimal_places=2)

    image = models.ImageField(upload_to='candles/')
    image2 = models.ImageField(upload_to='candles/', blank=True, null=True)
    image3 = models.ImageField(upload_to='candles/', blank=True, null=True)


    categories = models.ManyToManyField(
        Category,
        through='CandleCategory',
        related_name='candles',
        verbose_name='Категории',
        blank=True
    )
    

    order = models.PositiveIntegerField(default=0)
    is_hit = models.BooleanField(default=False)
    is_on_sale = models.BooleanField(default=False)
    discount_percent = models.PositiveSmallIntegerField(null=True, blank=True)

    collection = models.ForeignKey(
        Collection,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Коллекция по настроению',
    )

    def discounted_price(self):
        if self.is_on_sale and self.discount_percent:
            try:
                return (self.price * (100 - self.discount_percent)) / 100
            except Exception:
                return self.price
        return self.price


    def display_name(self):
        lang = (translation.get_language() or '').lower()
        # Swap display: if user selected Russian, show Ukrainian fields;
        # if user selected Ukrainian, show Russian fields.
        if lang.startswith('uk'):
            return self.name or self.name_ru or ''
        if lang.startswith('ru'):
            return self.name_ru or self.name or ''
        return self.name or self.name_ru or ''

    def display_description(self):
        lang = (translation.get_language() or '').lower()
        # Swap display for descriptions as well
        if lang.startswith('uk'):
            return self.description or self.description_ru or ''
        if lang.startswith('ru'):
            return self.description_ru or self.description or ''
        return self.description or self.description_ru or ''

    def __str__(self):
        return self.display_name()

    class Meta:
        ordering = ['order', '-id']


class CandleImage(models.Model):
    candle = models.ForeignKey(Candle, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='candles/')
    order = models.PositiveIntegerField(default=0, verbose_name='Порядок')

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f'{self.candle_id} #{self.id}'


class Order(models.Model):
    # Украинские поля
    full_name = models.CharField(max_length=200, verbose_name='ПІБ')
    phone = models.CharField(max_length=20, verbose_name='Телефон')
    email = models.EmailField(verbose_name='Електронна пошта')
    city = models.CharField(max_length=100, verbose_name='Населений пункт')
    warehouse = models.CharField(max_length=200, verbose_name='Відділення Нової пошти', blank=True, default='')
    payment_method = models.CharField(
        max_length=10,
        choices=[
            ('card', 'Оплата карткою'),
            ('cod', 'Накладений платіж'),
        ],
        blank=True,
        default='',
        verbose_name='Спосіб оплати',
    )
    notes = models.TextField(blank=True, null=True, verbose_name='Нотатки')
    agree_to_terms = models.BooleanField(default=False, verbose_name='Згода на обробку персональних даних')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ('new', 'Новий'),
            ('processing', 'В обробці'),
            ('sent', 'Відправлено'),
            ('delivered', 'Доставлено'),
            ('cancelled', 'Скасовано'),
        ],
        default='new',
        verbose_name='Статус'
    )
    
    class Meta:
        verbose_name_plural = 'Замовлення'
        ordering = ['-created_at']
    
    def __str__(self):
        return f'Замовлення #{self.id} - {self.full_name}'
    
    def get_total(self):
        return sum(item.get_subtotal() for item in self.items.all())


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    candle = models.ForeignKey(Candle, on_delete=models.SET_NULL, null=True)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    
    class Meta:
        verbose_name_plural = 'Товари в замовленні'
    
    def __str__(self):
        # candle can be None if the product was removed (on_delete=SET_NULL)
        if self.candle:
            try:
                name = self.candle.display_name()
            except Exception:
                name = str(self.candle)
        else:
            name = f'Удалённый товар (id={getattr(self, "candle_id", "?")})'
        return f'{name} x {self.quantity}'
    
    def get_subtotal(self):
        return self.price * self.quantity
