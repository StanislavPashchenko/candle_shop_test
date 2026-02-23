from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0006_candle_is_available'),
    ]

    operations = [
        migrations.AddField(
            model_name='productoptionvalue',
            name='image',
            field=models.ImageField(blank=True, null=True, upload_to='option_values/', verbose_name='Картинка для значения'),
        ),
    ]
