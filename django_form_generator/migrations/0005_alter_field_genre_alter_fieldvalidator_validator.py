# Generated by Django 4.1.1 on 2023-01-20 21:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('django_form_generator', '0004_fieldoptionthrough_remove_fieldvaluethrough_field_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='field',
            name='genre',
            field=models.CharField(choices=[('text_input', 'Text input'), ('multi_text_input', 'Multi-Text input'), ('text_area', 'Text area'), ('number', 'Number'), ('dropdown', 'Dropdown'), ('date', 'Date'), ('time', 'Time'), ('datetime', 'Datetime'), ('email', 'E-Mail'), ('password', 'Password'), ('checkbox', 'Checkbox'), ('multi_checkbox', 'Multi checkbox'), ('radio', 'Radio'), ('hidden', 'Hidden'), ('captcha', 'Captcha'), ('upload_file', 'Upload file')], max_length=80, verbose_name='Genre'),
        ),
        migrations.AlterField(
            model_name='fieldvalidator',
            name='validator',
            field=models.CharField(choices=[('max-length', 'Max length'), ('min-length', 'Min length'), ('max-value', 'Max value'), ('min-value', 'Min value'), ('regex', 'Regex'), ('file-extention', 'File extention'), ('file-size', 'File size (MB)')], max_length=100, verbose_name='Validator'),
        ),
    ]
