# Generated by Django 4.0.3 on 2022-11-30 12:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('varasto', '0058_alter_goods_cost_centre'),
    ]

    operations = [
        migrations.AddField(
            model_name='rental_event',
            name='returned',
            field=models.DecimalField(blank=True, decimal_places=4, max_digits=11, null=True),
        ),
    ]
