from django.db import models
from django.utils import translation
from django.core.validators import FileExtensionValidator


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


class HomeBanner(models.Model):
    title_uk = models.CharField(max_length=160, blank=True, verbose_name='Заголовок (укр)')
    title_ru = models.CharField(max_length=160, blank=True, null=True, verbose_name='Заголовок (рус)')
    subtitle_uk = models.TextField(blank=True, verbose_name='Текст (укр)')
    subtitle_ru = models.TextField(blank=True, null=True, verbose_name='Текст (рус)')
    cta_text_uk = models.CharField(max_length=80, blank=True, verbose_name='Текст кнопки (укр)')
    cta_text_ru = models.CharField(max_length=80, blank=True, null=True, verbose_name='Текст кнопки (рус)')
    cta_url = models.CharField(max_length=200, blank=True, verbose_name='Ссылка кнопки')
    order = models.PositiveIntegerField(default=0, verbose_name='Порядок отображения')
    duration_seconds = models.PositiveIntegerField(default=4, verbose_name='Время показа (сек)')
    media = models.FileField(
        upload_to='home_banner/',
        blank=True,
        null=True,
        verbose_name='Медиа',
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp', 'mp4', 'webm', 'ogg', 'ogv', 'mov', 'm4v'])]
    )
    is_active = models.BooleanField(default=True, verbose_name='Активный')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлено')

    class Meta:
        verbose_name = 'Баннер главной страницы'
        verbose_name_plural = 'Баннер главной страницы'
        ordering = ['-is_active', 'order', '-updated_at', '-id']

    def __str__(self):
        return self.display_title() or f'Banner #{self.id}'

    def display_title(self):
        lang = (translation.get_language() or '').lower()
        if lang.startswith('uk'):
            return self.title_uk or self.title_ru or ''
        if lang.startswith('ru'):
            return self.title_ru or self.title_uk or ''
        return self.title_uk or self.title_ru or ''

    def display_subtitle(self):
        lang = (translation.get_language() or '').lower()
        if lang.startswith('uk'):
            return self.subtitle_uk or self.subtitle_ru or ''
        if lang.startswith('ru'):
            return self.subtitle_ru or self.subtitle_uk or ''
        return self.subtitle_uk or self.subtitle_ru or ''

    def display_cta_text(self):
        lang = (translation.get_language() or '').lower()
        if lang.startswith('uk'):
            return self.cta_text_uk or self.cta_text_ru or ''
        if lang.startswith('ru'):
            return self.cta_text_ru or self.cta_text_uk or ''
        return self.cta_text_uk or self.cta_text_ru or ''

    @property
    def is_video(self):
        if not self.media or not self.media.name:
            return False
        ext = os.path.splitext(self.media.name)[1].lower().lstrip('.')
        return ext in {'mp4', 'webm', 'ogg', 'ogv', 'mov', 'm4v'}

    @property
    def duration_ms(self) -> int:
        try:
            sec = int(self.duration_seconds or 4)
        except Exception:
            sec = 4
        if sec < 1:
            sec = 1
        if sec > 60:
            sec = 60
        return sec * 1000


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

    is_available = models.BooleanField(default=True, verbose_name='В наличии')

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


# Удаление файлов изображений при удалении товара
from django.db.models.signals import post_delete
from django.dispatch import receiver
import os


@receiver(post_delete, sender=Candle)
def delete_candle_images(sender, instance, **kwargs):
    """Удаляет файлы изображений при удалении товара (Candle)."""
    for field_name in ['image', 'image2', 'image3']:
        field = getattr(instance, field_name, None)
        if field and field.name:
            try:
                if os.path.isfile(field.path):
                    os.remove(field.path)
            except Exception:
                pass



# =================== КОНФИГУРАТОР ТОВАРОВ ===================

class ProductOption(models.Model):
    """Конкретная опция товара с типом ввода."""
    INPUT_TYPE_CHOICES = [
        ('select', 'Выпадающий список'),
        ('radio', 'Радио-кнопки'),
        ('buttons', 'Кнопки'),
    ]

    product = models.ForeignKey(
        Candle,
        on_delete=models.CASCADE,
        related_name='options',
        verbose_name='Товар',
        null=True,
        blank=True
    )
    name = models.CharField(max_length=100, verbose_name='Название опции (укр)')
    name_ru = models.CharField(max_length=100, blank=True, null=True, verbose_name='Название опции (рус)')
    is_required = models.BooleanField(default=True, verbose_name='Обязательная')
    input_type = models.CharField(
        max_length=10,
        choices=INPUT_TYPE_CHOICES,
        default='select',
        verbose_name='Тип ввода'
    )
    sort_order = models.PositiveIntegerField(default=0, verbose_name='Порядок сортировки')

    class Meta:
        verbose_name = 'Опция товара'
        verbose_name_plural = 'Опции товара'
        ordering = ['sort_order', 'id']
        unique_together = ('product', 'name')

    def __str__(self):
        req = 'обяз.' if self.is_required else 'необяз.'
        return f'{self.product.display_name()} — {self.display_name()} ({req})'

    def display_name(self):
        """Возвращает название опции на текущем языке."""
        lang = (translation.get_language() or '').lower()
        if lang.startswith('ru'):
            return self.name_ru or self.name or ''
        return self.name or self.name_ru or ''


class ProductOptionValue(models.Model):
    """Значение опции (например, "белый", "чёрный")."""
    option = models.ForeignKey(
        ProductOption,
        on_delete=models.CASCADE,
        related_name='values',
        verbose_name='Опция'
    )
    value = models.CharField(max_length=100, verbose_name='Значение (укр)')
    value_ru = models.CharField(max_length=100, blank=True, null=True, verbose_name='Значение (рус)')
    image = models.ImageField(
        upload_to='option_values/',
        blank=True,
        null=True,
        verbose_name='Картинка для значения'
    )
    sort_order = models.PositiveIntegerField(default=0, verbose_name='Порядок сортировки')
    price_modifier = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
        blank=True,
        verbose_name='Изменение цены (+/-)'
    )

    class Meta:
        verbose_name = 'Значение опции'
        verbose_name_plural = 'Значения опций'
        ordering = ['sort_order', 'id']

    def __str__(self):
        if self.price_modifier:
            return f'{self.display_value()} ({"+" if self.price_modifier > 0 else ""}{self.price_modifier} ₴)'
        return self.display_value()

    def display_value(self):
        """Возвращает значение на текущем языке."""
        lang = (translation.get_language() or '').lower()
        if lang.startswith('ru'):
            return self.value_ru or self.value or ''
        return self.value or self.value_ru or ''


# Расширение OrderItem для хранения выбранных опций
class OrderItemOption(models.Model):
    """Выбранная опция для позиции в заказе."""
    order_item = models.ForeignKey(
        OrderItem,
        on_delete=models.CASCADE,
        related_name='selected_options',
        verbose_name='Позиция заказа'
    )
    option_name = models.CharField(max_length=100, verbose_name='Название опции')
    value_name = models.CharField(max_length=100, verbose_name='Выбранное значение')
    price_modifier = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
        verbose_name='Изменение цены'
    )

    class Meta:
        verbose_name = 'Выбранная опция'
        verbose_name_plural = 'Выбранные опции'

    def __str__(self):
        return f'{self.option_name}: {self.value_name}'


# Удаление файлов изображений при удалении товара
from django.db.models.signals import post_delete
from django.dispatch import receiver
import os


@receiver(post_delete, sender=Candle)
def delete_candle_images(sender, instance, **kwargs):
    """Удаляет файлы изображений при удалении товара (Candle)."""
    for field_name in ['image', 'image2', 'image3']:
        field = getattr(instance, field_name, None)
        if field and field.name:
            try:
                if os.path.isfile(field.path):
                    os.remove(field.path)
            except Exception:
                pass


@receiver(post_delete, sender=CandleImage)
def delete_candle_image_file(sender, instance, **kwargs):
    """Удаляет файл изображения при удалении записи CandleImage."""
    if instance.image and instance.image.name:
        try:
            if os.path.isfile(instance.image.path):
                os.remove(instance.image.path)
        except Exception:
            pass


@receiver(post_delete, sender=ProductOptionValue)
def delete_product_option_value_image(sender, instance, **kwargs):
    if instance.image and instance.image.name:
        try:
            if os.path.isfile(instance.image.path):
                os.remove(instance.image.path)
        except Exception:
            pass

@receiver(post_delete, sender=Collection)
def delete_collection_banner(sender, instance, **kwargs):
    if instance.banner and instance.banner.name:
        try:
            if os.path.isfile(instance.banner.path):
                os.remove(instance.banner.path)
        except Exception:
            pass


@receiver(post_delete, sender=HomeBanner)
def delete_home_banner_media(sender, instance, **kwargs):
    if instance.media and instance.media.name:
        try:
            if os.path.isfile(instance.media.path):
                os.remove(instance.media.path)
        except Exception:
            pass


class ScentCategoryGroup(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name='Название группы (укр)')
    name_ru = models.CharField(max_length=100, blank=True, null=True, verbose_name='Название группы (рус)')
    order = models.PositiveIntegerField(default=0, verbose_name='Порядок')

    class Meta:
        verbose_name_plural = 'Группы категорий ароматов'
        ordering = ['order', 'name']

    def __str__(self):
        return self.display_name()

    def display_name(self):
        lang = (translation.get_language() or '').lower()
        if lang.startswith('ru'):
            return self.name_ru or self.name or ''
        return self.name or self.name_ru or ''


class ScentCategory(models.Model):
    group = models.ForeignKey(
        ScentCategoryGroup,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='categories',
        verbose_name='Группа',
    )
    name = models.CharField(max_length=100, unique=True, verbose_name='Название категории (укр)')
    name_ru = models.CharField(max_length=100, blank=True, null=True, verbose_name='Название категории (рус)')
    order = models.PositiveIntegerField(default=0, verbose_name='Порядок')

    class Meta:
        verbose_name = 'Категория аромата'
        verbose_name_plural = 'Ароматы категории'
        ordering = ['group__order', 'group__name', 'order', 'name']

    def __str__(self):
        return self.display_name()

    def display_name(self):
        lang = (translation.get_language() or '').lower()
        if lang.startswith('ru'):
            return self.name_ru or self.name or ''
        return self.name or self.name_ru or ''


class ScentCategoryLink(models.Model):
    scent = models.ForeignKey(
        'Scent',
        on_delete=models.CASCADE,
        related_name='category_links'
    )
    category = models.ForeignKey(
        'ScentCategory',
        on_delete=models.CASCADE,
        related_name='scent_links'
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']
        unique_together = ('scent', 'category')


class Scent(models.Model):
    """Ароматы/запахи для отдельной страницы с описанием."""
    name = models.CharField(max_length=100, verbose_name='Название аромата (укр)')
    name_ru = models.CharField(max_length=100, blank=True, null=True, verbose_name='Название аромата (рус)')
    description = models.TextField(blank=True, verbose_name='Описание аромата (укр)')
    description_ru = models.TextField(blank=True, null=True, verbose_name='Описание аромата (рус)')
    image = models.ImageField(upload_to='scents/', blank=True, null=True, verbose_name='Картинка аромата')
    categories = models.ManyToManyField(
        ScentCategory,
        through='ScentCategoryLink',
        related_name='scents',
        verbose_name='Категории ароматов',
        blank=True,
    )
    order = models.PositiveIntegerField(default=0, verbose_name='Порядок')

    class Meta:
        verbose_name = 'Аромат'
        verbose_name_plural = 'Ароматы'
        ordering = ['order', 'name']

    def __str__(self):
        return self.display_name()

    def display_name(self):
        """Возвращает название аромата на текущем языке."""
        lang = (translation.get_language() or '').lower()
        if lang.startswith('ru'):
            return self.name_ru or self.name or ''
        return self.name or self.name_ru or ''

    def display_description(self):
        """Возвращает описание аромата на текущем языке."""
        lang = (translation.get_language() or '').lower()
        if lang.startswith('ru'):
            return self.description_ru or self.description or ''
        return self.description or self.description_ru or ''


# Удаление файлов изображений при удалении аромата
@receiver(post_delete, sender=Scent)
def delete_scent_image(sender, instance, **kwargs):
    """Удаляет файл изображения при удалении аромата."""
    if instance.image and instance.image.name:
        try:
            if os.path.isfile(instance.image.path):
                os.remove(instance.image.path)
        except Exception:
            pass
