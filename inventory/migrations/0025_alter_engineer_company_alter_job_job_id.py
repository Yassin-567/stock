# Generated by Django 5.2 on 2025-05-12 19:55

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0024_alter_engineer_company'),
    ]

    operations = [
        migrations.AlterField(
            model_name='engineer',
            name='company',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='engineers_company', to='inventory.company'),
        ),
        migrations.AlterField(
            model_name='job',
            name='job_id',
            field=models.BigIntegerField(),
        ),
    ]
