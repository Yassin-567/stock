# Generated by Django 5.1.6 on 2025-04-30 18:31

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0018_remove_warehouseitem_arrived_quantity'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='item',
            name='status',
        ),
    ]
