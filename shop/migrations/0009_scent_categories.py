from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0008_add_scent_model'),
    ]

    operations = [
        migrations.CreateModel(
            name='ScentCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True, verbose_name='Название категории (укр)')),
                ('name_ru', models.CharField(blank=True, max_length=100, null=True, verbose_name='Название категории (рус)')),
                ('order', models.PositiveIntegerField(default=0, verbose_name='Порядок')),
            ],
            options={
                'verbose_name': 'Категория аромата',
                'verbose_name_plural': 'Ароматы категории',
                'ordering': ['order', 'name'],
            },
        ),
        migrations.AddField(
            model_name='scent',
            name='categories',
            field=models.ManyToManyField(blank=True, related_name='scents', to='shop.scentcategory', verbose_name='Категории ароматов'),
        ),
    ]
