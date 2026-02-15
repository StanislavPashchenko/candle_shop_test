from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0016_candle_image2_candle_image3'),
    ]

    operations = [
        migrations.CreateModel(
            name='CategoryGroup',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True, verbose_name='Название группы (укр)')),
                ('name_ru', models.CharField(blank=True, max_length=100, null=True, verbose_name='Название группы (рус)')),
                ('order', models.PositiveIntegerField(default=0, verbose_name='Порядок')),
            ],
            options={
                'verbose_name_plural': 'Группы категорий',
                'ordering': ['order', 'name'],
            },
        ),
        migrations.AddField(
            model_name='category',
            name='group',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='categories', to='shop.categorygroup', verbose_name='Группа'),
        ),
        migrations.AlterField(
            model_name='category',
            name='name',
            field=models.CharField(max_length=100, verbose_name='Название (укр)'),
        ),
        migrations.AlterModelOptions(
            name='category',
            options={'ordering': ['group__order', 'group__name', 'order', 'name'], 'verbose_name_plural': 'Категории'},
        ),
        migrations.AddConstraint(
            model_name='category',
            constraint=models.UniqueConstraint(fields=('group', 'name'), name='uniq_category_group_name_uk'),
        ),
    ]
