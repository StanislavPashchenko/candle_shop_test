import django.db.models.deletion
from django.db import migrations, models


def copy_scent_categories(apps, schema_editor):
    ScentCategoryLink = apps.get_model('shop', 'ScentCategoryLink')
    connection = schema_editor.connection
    table_name = 'shop_scent_categories'
    if table_name not in connection.introspection.table_names():
        return
    with connection.cursor() as cursor:
        cursor.execute(f'SELECT scent_id, scentcategory_id FROM {table_name}')
        rows = cursor.fetchall()
    if not rows:
        return
    links = [
        ScentCategoryLink(scent_id=scent_id, category_id=category_id, order=0)
        for scent_id, category_id in rows
    ]
    ScentCategoryLink.objects.bulk_create(links, ignore_conflicts=True)


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0009_scent_categories'),
    ]

    operations = [
        migrations.CreateModel(
            name='ScentCategoryLink',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order', models.PositiveIntegerField(default=0)),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='scent_links', to='shop.scentcategory')),
                ('scent', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='category_links', to='shop.scent')),
            ],
            options={
                'ordering': ['order'],
                'unique_together': {('scent', 'category')},
            },
        ),
        migrations.RunPython(copy_scent_categories, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='scent',
            name='categories',
        ),
        migrations.AddField(
            model_name='scent',
            name='categories',
            field=models.ManyToManyField(blank=True, related_name='scents', through='shop.ScentCategoryLink', to='shop.scentcategory', verbose_name='Категории ароматов'),
        ),
    ]
