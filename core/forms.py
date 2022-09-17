from django import forms
from django.conf import settings
from django.core.validators import MinValueValidator, FileExtensionValidator
from django.core.cache import cache
from django.utils.translation import gettext as _
from captcha.fields import ReCaptchaField
from captcha.widgets import ReCaptchaV2Checkbox

from core.models import Field, Form, FormDetail, FormResponse, FormTemplate


class CustomeSelectFormField(forms.Select):
    option_inherits_attrs = True


class FormGeneratorForm(forms.Form):
    
    def __init__(self, form_detail, user_ip, *args, ignore_disabled=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance = form_detail
        self.user_ip = user_ip
        self.ignore_disabled = ignore_disabled
        self.template_name_p = self.instance.template.get_directory
        for field in self.instance.form.get_fields():
            method = f'prepare_{field.genre}'
            if hasattr(self, method):
                field_name = field.name.replace(' ', '_')
                form_field = getattr(self, method)(field)
                self.fields[field_name] = form_field

    def save(self):
        api_response = []
        form_data = self.cleaned_data
        if self.instance.send_mail:
            self.instance.send_email(form_data)
        pre_result = cache.get(f'Form_APIs_{self.instance.form.pk}_pre', [])
        post_result = self.instance.form.call_post_apis(form_data)
        api_response.append(self.generate_api_result(pre_result))
        api_response.append(self.generate_api_result(post_result))
        FormResponse.objects.create(data=self.generate_data(), 
                                    user_ip=self.user_ip, 
                                    api_response=api_response, 
                                    form=self.instance.form)
        return self.instance

    def generate_api_result(self, results):
        data = []
        for api, status_code, result in results:
            data.append({
                "api": api.id,
                "url": api.url,
                "method": api.method,
                "body": api.body,
                "response_status_code": status_code,
                "result": result
            })
        return data


    def generate_data(self):
        data = []
        for field in self.instance.form.get_fields():
            data.append(
                {
                    "id": field.id,
                    "name": field.name,
                    "label": field.label,
                    "genre": field.genre,
                    "category": getattr(field, 'category'),
                    "value": self.cleaned_data[field.name]
                }
            )
        return data

    def prepare_text_input(self, field: Field):
        widget_attrs = field.build_widget_attrs({'content_type': 'field'})
        field_attrs: dict = field.build_field_attrs({'widget': forms.TextInput(attrs=widget_attrs)})
        if self.ignore_disabled:
            field_attrs.pop('disabled', None)
        return forms.CharField(**field_attrs)

    def prepare_text_area(self, field: Field):
        widget_attrs = field.build_widget_attrs({'content_type': 'field'})
        field_attrs = field.build_field_attrs({'widget': forms.Textarea(attrs=widget_attrs)})
        if self.ignore_disabled:
            field_attrs.pop('disabled', None)
        return forms.CharField(**field_attrs)

    def prepare_number(self, field: Field):
        widget_attrs = field.build_widget_attrs({'content_type': 'field'})
        field_attrs = field.build_field_attrs({'widget': forms.NumberInput(attrs=widget_attrs)})
        if self.ignore_disabled:
            field_attrs.pop('disabled', None)
        return forms.IntegerField(**field_attrs)

    def prepare_data(self, field:Field):
        widget_attrs = field.build_widget_attrs({'content_type': 'field'})
        field_attrs = field.build_field_attrs({'widget': forms.DateInput(attrs=widget_attrs)})
        if self.ignore_disabled:
            field_attrs.pop('disabled', None)
        return forms.DateField(**field_attrs)

    def prepare_time(self, field:Field):
        widget_attrs = field.build_widget_attrs({'content_type': 'field'})
        field_attrs = field.build_field_attrs({'widget': forms.TimeInput(attrs=widget_attrs)})
        if self.ignore_disabled:
            field_attrs.pop('disabled', None)
        return forms.TimeField(**field_attrs)

    def prepare_datetime(self, field:Field):
        widget_attrs = field.build_widget_attrs({'content_type': 'field'})
        field_attrs = field.build_field_attrs({'widget': forms.DateTimeInput(attrs=widget_attrs)})
        if self.ignore_disabled:
            field_attrs.pop('disabled', None)
        return forms.DateTimeField(**field_attrs)
        
    def prepare_email(self, field:Field):
        widget_attrs = field.build_widget_attrs({'content_type': 'field'})
        field_attrs = field.build_field_attrs({'widget': forms.EmailInput(attrs=widget_attrs)})
        if self.ignore_disabled:
            field_attrs.pop('disabled', None)
        return forms.EmailField(**field_attrs)

    def prepare_password(self, field:Field):
        widget_attrs = field.build_widget_attrs({'content_type': 'field'})
        field_attrs = field.build_field_attrs({'widget': forms.PasswordInput(attrs=widget_attrs)})
        if self.ignore_disabled:
            field_attrs.pop('disabled', None)
        return forms.CharField(**field_attrs)

    def prepare_checkbox(self, field:Field):
        widget_attrs = field.build_widget_attrs({'content_type': 'field'})
        field_attrs = field.build_field_attrs({'widget': forms.CheckboxInput(attrs=widget_attrs)})
        if self.ignore_disabled:
            field_attrs.pop('disabled', None)
        return forms.BooleanField(**field_attrs)

    def prepare_dropdown(self, field: Field):
        widget_attrs = field.build_widget_attrs({'content_type': 'value'})
        choices = field.get_choices().values_list('id', 'name')
        field_attrs = field.build_field_attrs({'widget': CustomeSelectFormField(attrs=widget_attrs),
                                                'choices': tuple(choices)})
        if self.ignore_disabled:
            field_attrs.pop('disabled', None)
        return forms.ChoiceField(**field_attrs)

    def prepare_multi_checkbox(self, field:Field):
        widget_attrs = field.build_widget_attrs({'content_type': 'value'})
        choices = field.get_choices().values_list('id', 'name')
        field_attrs = field.build_field_attrs({'widget': forms.CheckboxSelectMultiple(attrs=widget_attrs),
                                                'choices': tuple(choices)})
        if self.ignore_disabled:
            field_attrs.pop('disabled', None)
        return forms.MultipleChoiceField(**field_attrs)

    def prepare_radio(self, field:Field):
        widget_attrs = field.build_widget_attrs({'content_type': 'value'})
        choices = field.get_choices().values_list('id', 'name')
        field_attrs = field.build_field_attrs({'widget': forms.RadioSelect(attrs=widget_attrs),
                                                'choices': tuple(choices)})
        if self.ignore_disabled:
            field_attrs.pop('disabled', None)
        return forms.ChoiceField(**field_attrs)

    def prepare_hidden(self, field:Field):
        widget_attrs = field.build_widget_attrs({'content_type': 'field'})
        field_attrs = field.build_field_attrs({'widget': forms.HiddenInput(attrs=widget_attrs)})
        if self.ignore_disabled:
            field_attrs.pop('disabled', None)
        return forms.CharField(**field_attrs)

    def prepare_captcha(self, field:Field):
        widget_attrs = field.build_widget_attrs({'content_type': 'field'})
        field_attrs = field.build_field_attrs({'widget': ReCaptchaV2Checkbox(attrs=widget_attrs)})
        if self.ignore_disabled:
            field_attrs.pop('disabled', None)
        return ReCaptchaField(**field_attrs)

    def prepare_upload_file(self, field:Field):
        message = _('The file size is more than limit (limited size: %s)') % field.file_size
        widget_attrs = field.build_widget_attrs({'multiple': True, 'content_type': 'field'})
        field_attrs = field.build_field_attrs({'widget': forms.ClearableFileInput(attrs=widget_attrs),
                                                'validators': [MinValueValidator(field.file_size, message), 
                                                            FileExtensionValidator(field.get_file_types())]})
        return forms.FileField(**field_attrs)



class FormTemplateForm(forms.ModelForm):

	directory = forms.FilePathField(str(settings.BASE_DIR / 'core/templates/form_generator/forms/'), recursive=True)

	class Meta:
		model = FormTemplate
		fields = '__all__'