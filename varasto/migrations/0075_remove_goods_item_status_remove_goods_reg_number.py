# Generated by Django 4.0.3 on 2023-03-06 11:11

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('varasto', '0074_customuser_is_storage_staff'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='goods',
            name='item_status',
        ),
        migrations.RemoveField(
            model_name='goods',
            name='reg_number',
        ),
    ]
