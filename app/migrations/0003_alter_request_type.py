# Generated by Django 4.2.7 on 2023-11-21 22:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0002_request_manual'),
    ]

    operations = [
        migrations.AlterField(
            model_name='request',
            name='type',
            field=models.CharField(choices=[('attract', 'requests to be with'), ('repel', 'requests not to be with'), ('forbid', 'must not be with'), ('require', 'must be with')], default='attract', max_length=20),
        ),
    ]
