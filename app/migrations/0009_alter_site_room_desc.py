# Generated by Django 4.2.7 on 2024-01-30 20:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0008_site'),
    ]

    operations = [
        migrations.AlterField(
            model_name='site',
            name='room_desc',
            field=models.TextField(default='{}'),
        ),
    ]
