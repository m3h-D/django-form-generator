from django import forms
from django.conf import settings
from django.core.validators import MinValueValidator, FileExtensionValidator
from django.utils.translation import gettext as _
from django.utils.module_loading import import_string

from captcha.fields import ReCaptchaField
from captcha.widgets import ReCaptchaV2Checkbox

from core.models import Field, Form, FormTemplate


class CustomeSelectFormField(forms.Select):
    option_inherits_attrs = True


class FormGeneratorForm(forms.Form):
    
    def __init__(self, request, instance, user_ip, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_ip = user_ip
        self.instance: Form = instance
        self.request = request
        self.template_name_p = getattr(self.instance.template, 'get_directory', self.template_name_p)
        for field in self.instance.get_fields():
            field_name = field.name
            method = f'prepare_{field.genre}'
            if hasattr(self, method):
                self.fields[field_name] =  getattr(self, method)(field)
            if self.data and self.fields[field_name].disabled:
                self.fields[field_name].disabled = False
                self.fields[field_name].initial = self.data.get(field_name, None)



    def save(self):
        form_data = self.cleaned_data.copy()
        form_data.setdefault('request', self.request)
        save_module = import_string(settings.FORM_RESPONSE_SAVE)
        save_module(self.instance, form_data, self.user_ip)

    def prepare_text_input(self, field: Field):
        widget_attrs: dict = field.build_widget_attrs(self.instance, {'content_type': 'field'})
        field_attrs: dict = field.build_field_attrs({'widget': forms.TextInput(attrs=widget_attrs)})
        return forms.CharField(**field_attrs)

    def prepare_text_area(self, field: Field):
        widget_attrs: dict = field.build_widget_attrs(self.instance, {'content_type': 'field'})
        field_attrs: dict = field.build_field_attrs({'widget': forms.Textarea(attrs=widget_attrs)})
        return forms.CharField(**field_attrs)

    def prepare_number(self, field: Field):
        widget_attrs: dict = field.build_widget_attrs(self.instance, {'content_type': 'field'})
        field_attrs: dict = field.build_field_attrs({'widget': forms.NumberInput(attrs=widget_attrs)})
        return forms.IntegerField(**field_attrs)

    def prepare_data(self, field:Field):
        widget_attrs: dict = field.build_widget_attrs(self.instance, {'content_type': 'field'})
        field_attrs: dict = field.build_field_attrs({'widget': forms.DateInput(attrs=widget_attrs)})
        return forms.DateField(**field_attrs)

    def prepare_time(self, field:Field):
        widget_attrs: dict = field.build_widget_attrs(self.instance, {'content_type': 'field'})
        field_attrs: dict = field.build_field_attrs({'widget': forms.TimeInput(attrs=widget_attrs)})
        return forms.TimeField(**field_attrs)

    def prepare_datetime(self, field:Field):
        widget_attrs: dict = field.build_widget_attrs(self.instance, {'content_type': 'field'})
        field_attrs: dict = field.build_field_attrs({'widget': forms.DateTimeInput(attrs=widget_attrs)})
        return forms.DateTimeField(**field_attrs)
        
    def prepare_email(self, field:Field):
        widget_attrs: dict = field.build_widget_attrs(self.instance, {'content_type': 'field'})
        field_attrs: dict = field.build_field_attrs({'widget': forms.EmailInput(attrs=widget_attrs)})
        return forms.EmailField(**field_attrs)

    def prepare_password(self, field:Field):
        widget_attrs: dict = field.build_widget_attrs(self.instance, {'content_type': 'field'})
        field_attrs: dict = field.build_field_attrs({'widget': forms.PasswordInput(attrs=widget_attrs)})
        return forms.CharField(**field_attrs)

    def prepare_checkbox(self, field:Field):
        widget_attrs: dict = field.build_widget_attrs(self.instance, {'content_type': 'field'})
        field_attrs: dict = field.build_field_attrs({'widget': forms.CheckboxInput(attrs=widget_attrs)})
        return forms.BooleanField(**field_attrs)

    def prepare_dropdown(self, field: Field):
        widget_attrs: dict = field.build_widget_attrs(self.instance, {'content_type': 'value'})
        choices = field.get_choices().values_list('id', 'name')
        field_attrs: dict = field.build_field_attrs({'widget': CustomeSelectFormField(attrs=widget_attrs),
                                                'choices': tuple(choices)})
        return forms.ChoiceField(**field_attrs)

    def prepare_multi_checkbox(self, field:Field):
        widget_attrs: dict = field.build_widget_attrs(self.instance, {'content_type': 'value'})
        choices = field.get_choices().values_list('id', 'name')
        field_attrs: dict = field.build_field_attrs({'widget': forms.CheckboxSelectMultiple(attrs=widget_attrs),
                                                'choices': tuple(choices)})
        return forms.MultipleChoiceField(**field_attrs)

    def prepare_radio(self, field:Field):
        widget_attrs: dict = field.build_widget_attrs(self.instance, {'content_type': 'value'})
        choices = field.get_choices().values_list('id', 'name')
        field_attrs: dict = field.build_field_attrs({'widget': forms.RadioSelect(attrs=widget_attrs),
                                                'choices': tuple(choices)})
        return forms.ChoiceField(**field_attrs)

    def prepare_hidden(self, field:Field):
        widget_attrs: dict = field.build_widget_attrs(self.instance, {'content_type': 'field'})
        field_attrs: dict = field.build_field_attrs({'widget': forms.HiddenInput(attrs=widget_attrs)})
        return forms.CharField(**field_attrs)

    def prepare_captcha(self, field:Field):
        widget_attrs: dict = field.build_widget_attrs(self.instance, {'content_type': 'field'})
        field_attrs: dict = field.build_field_attrs({'widget': ReCaptchaV2Checkbox(attrs=widget_attrs)})
        return ReCaptchaField(**field_attrs)

    def prepare_upload_file(self, field:Field):
        message = _('The file size is more than limit (limited size: %s)') % field.file_size
        widget_attrs: dict = field.build_widget_attrs(self.instance, {'multiple': True, 'content_type': 'field'})
        field_attrs: dict = field.build_field_attrs({'widget': forms.ClearableFileInput(attrs=widget_attrs),
                                                'validators': [MinValueValidator(field.file_size, message), 
                                                            FileExtensionValidator(field.get_file_types())]})
        return forms.FileField(**field_attrs)



class FormTemplateForm(forms.ModelForm):

	directory = forms.FilePathField(str(settings.BASE_DIR / 'core/templates/core/fields/'), recursive=True)

	class Meta:
		model = FormTemplate
		fields = '__all__'