# Generated by Django 5.2 on 2025-04-19 19:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0003_comment_company'),
    ]

    operations = [
        migrations.AddField(
            model_name='item',
            name='is_warehouse_item',
            field=models.BooleanField(default=False),
        ),
    ]
