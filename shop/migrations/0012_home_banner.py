from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0011_scent_category_groups'),
    ]

    operations = [
        migrations.CreateModel(
            name='HomeBanner',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title_uk', models.CharField(blank=True, max_length=160, verbose_name='Заголовок (укр)')),
                ('title_ru', models.CharField(blank=True, max_length=160, null=True, verbose_name='Заголовок (рус)')),
                ('subtitle_uk', models.TextField(blank=True, verbose_name='Текст (укр)')),
                ('subtitle_ru', models.TextField(blank=True, null=True, verbose_name='Текст (рус)')),
                ('cta_text_uk', models.CharField(blank=True, max_length=80, verbose_name='Текст кнопки (укр)')),
                ('cta_text_ru', models.CharField(blank=True, max_length=80, null=True, verbose_name='Текст кнопки (рус)')),
                ('cta_url', models.CharField(blank=True, max_length=200, verbose_name='Ссылка кнопки')),
                ('media', models.FileField(blank=True, null=True, upload_to='home_banner/', validators=[django.core.validators.FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp', 'mp4', 'webm', 'ogg', 'ogv', 'mov', 'm4v'])], verbose_name='Медиа')),
                ('is_active', models.BooleanField(default=True, verbose_name='Активный')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Обновлено')),
            ],
            options={
                'verbose_name': 'Баннер главной страницы',
                'verbose_name_plural': 'Баннер главной страницы',
                'ordering': ['-is_active', '-updated_at', '-id'],
            },
        ),
    ]
