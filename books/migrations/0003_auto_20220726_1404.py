# Generated by Django 3.2 on 2022-07-26 14:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('books', '0002_book_suitable_for_ages'),
    ]

    operations = [
        migrations.AddField(
            model_name='book',
            name='discount',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True),
        ),
        migrations.AddField(
            model_name='book',
            name='is_new',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='book',
            name='sale_price',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True),
        ),
    ]
