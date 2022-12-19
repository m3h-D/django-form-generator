# Generated by Django 4.1.1 on 2022-12-18 07:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('django_form_generator', '0001_initial'),
    ]

    operations = [
            migrations.AddField(
                model_name='field',
                name='read_only',
                field=models.BooleanField(default=False, verbose_name='Read Only'),
            ),
            migrations.AddField(
                model_name='field',
                name='write_only',
                field=models.BooleanField(default=False, verbose_name='Write Only'),
            ),
    ]
