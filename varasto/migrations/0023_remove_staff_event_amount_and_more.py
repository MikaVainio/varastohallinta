# Generated by Django 4.0.3 on 2022-05-10 10:45

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('varasto', '0022_alter_goods_ean_alter_rental_event_start_date'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='staff_event',
            name='amount',
        ),
        migrations.AlterField(
            model_name='rental_event',
            name='start_date',
            field=models.DateTimeField(blank=True, null=True, verbose_name=datetime.datetime(2022, 5, 10, 13, 45, 40, 931471)),
        ),
    ]
