# Generated by Django 4.0.3 on 2022-06-21 09:37

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('varasto', '0031_alter_customuser_storge_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='customuser',
            old_name='storge',
            new_name='storage',
        ),
        migrations.AlterField(
            model_name='rental_event',
            name='start_date',
            field=models.DateTimeField(blank=True, null=True, verbose_name=datetime.datetime(2022, 6, 21, 12, 37, 32, 597632)),
        ),
    ]
