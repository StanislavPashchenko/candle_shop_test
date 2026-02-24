from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0010_scent_category_links'),
    ]

    operations = [
        migrations.CreateModel(
            name='ScentCategoryGroup',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True, verbose_name='Название группы (укр)')),
                ('name_ru', models.CharField(blank=True, max_length=100, null=True, verbose_name='Название группы (рус)')),
                ('order', models.PositiveIntegerField(default=0, verbose_name='Порядок')),
            ],
            options={
                'verbose_name_plural': 'Группы категорий ароматов',
                'ordering': ['order', 'name'],
            },
        ),
        migrations.AddField(
            model_name='scentcategory',
            name='group',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='categories', to='shop.scentcategorygroup', verbose_name='Группа'),
        ),
    ]
