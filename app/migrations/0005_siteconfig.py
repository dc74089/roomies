# Generated by Django 4.2.7 on 2023-11-22 20:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0004_solution_added_solution_explanation'),
    ]

    operations = [
        migrations.CreateModel(
            name='SiteConfig',
            fields=[
                ('id', models.CharField(max_length=100, primary_key=True, serialize=False)),
                ('val', models.BooleanField(default=False)),
            ],
        ),
    ]
