from django import forms
from django.core.validators import FileExtensionValidator
from django.utils.translation import gettext as _

from captcha.fields import ReCaptchaField
from captcha.widgets import ReCaptchaV2Checkbox

from django_form_generator.settings import form_generator_settings as fg_settings
from django_form_generator.common.utils import FileSizeValidator
from django_form_generator.models import Field, Form
from django_form_generator import const


class CustomeSelectFormField(forms.Select):
    option_inherits_attrs = True


class FormGeneratorBaseForm(forms.Form):
    def __init__(self, form, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance = form
        self.template_name_p = getattr(self.instance, "theme", self.template_name_p)
        for field in self.instance.get_fields():
            method = f"prepare_{field.genre}"
            if hasattr(self, method):
                self.fields[field.name] = getattr(self, method)(field)

    def prepare_text_input(self, field: Field):
        widget_attrs: dict = field.build_widget_attrs(
            self.instance, {"content_type": "field"}
        )
        field_attrs: dict = field.build_field_attrs(
            {"widget": forms.TextInput(attrs=widget_attrs)}
        )
        return forms.CharField(**field_attrs)

    def prepare_text_area(self, field: Field):
        widget_attrs: dict = field.build_widget_attrs(
            self.instance, {"content_type": "field"}
        )
        field_attrs: dict = field.build_field_attrs(
            {"widget": forms.Textarea(attrs=widget_attrs)}
        )
        return forms.CharField(**field_attrs)

    def prepare_number(self, field: Field):
        widget_attrs: dict = field.build_widget_attrs(
            self.instance, {"content_type": "field"}
        )
        field_attrs: dict = field.build_field_attrs(
            {"widget": forms.NumberInput(attrs=widget_attrs)}
        )
        return forms.IntegerField(**field_attrs)

    def prepare_data(self, field: Field):
        widget_attrs: dict = field.build_widget_attrs(
            self.instance, {"content_type": "field"}
        )
        field_attrs: dict = field.build_field_attrs(
            {"widget": forms.DateInput(attrs=widget_attrs)}
        )
        return forms.DateField(**field_attrs)

    def prepare_time(self, field: Field):
        widget_attrs: dict = field.build_widget_attrs(
            self.instance, {"content_type": "field"}
        )
        field_attrs: dict = field.build_field_attrs(
            {"widget": forms.TimeInput(attrs=widget_attrs)}
        )
        return forms.TimeField(**field_attrs)

    def prepare_datetime(self, field: Field):
        widget_attrs: dict = field.build_widget_attrs(
            self.instance, {"content_type": "field"}
        )
        field_attrs: dict = field.build_field_attrs(
            {"widget": forms.DateTimeInput(attrs=widget_attrs)}
        )
        return forms.DateTimeField(**field_attrs)

    def prepare_email(self, field: Field):
        widget_attrs: dict = field.build_widget_attrs(
            self.instance, {"content_type": "field"}
        )
        field_attrs: dict = field.build_field_attrs(
            {"widget": forms.EmailInput(attrs=widget_attrs)}
        )
        return forms.EmailField(**field_attrs)

    def prepare_password(self, field: Field):
        widget_attrs: dict = field.build_widget_attrs(
            self.instance, {"content_type": "field"}
        )
        field_attrs: dict = field.build_field_attrs(
            {"widget": forms.PasswordInput(attrs=widget_attrs)}
        )
        return forms.CharField(**field_attrs)

    def prepare_checkbox(self, field: Field):
        widget_attrs: dict = field.build_widget_attrs(
            self.instance, {"content_type": "field"}
        )
        field_attrs: dict = field.build_field_attrs(
            {"widget": forms.CheckboxInput(attrs=widget_attrs)}
        )
        return forms.BooleanField(**field_attrs)

    def prepare_dropdown(self, field: Field):
        widget_attrs: dict = field.build_widget_attrs(
            self.instance, {"content_type": "value"}
        )
        choices = field.get_choices().values_list("id", "name")
        field_attrs: dict = field.build_field_attrs(
            {
                "widget": CustomeSelectFormField(attrs=widget_attrs),
                "choices": tuple(choices),
            }
        )
        return forms.ChoiceField(**field_attrs)

    def prepare_multi_checkbox(self, field: Field):
        widget_attrs: dict = field.build_widget_attrs(
            self.instance, {"content_type": "value"}
        )
        choices = field.get_choices().values_list("id", "name")
        field_attrs: dict = field.build_field_attrs(
            {
                "widget": forms.CheckboxSelectMultiple(attrs=widget_attrs),
                "choices": tuple(choices),
            }
        )
        return forms.MultipleChoiceField(**field_attrs)

    def prepare_radio(self, field: Field):
        widget_attrs: dict = field.build_widget_attrs(
            self.instance, {"content_type": "value"}
        )
        choices = field.get_choices().values_list("id", "name")
        field_attrs: dict = field.build_field_attrs(
            {"widget": forms.RadioSelect(attrs=widget_attrs), "choices": tuple(choices)}
        )
        return forms.ChoiceField(**field_attrs)

    def prepare_hidden(self, field: Field):
        widget_attrs: dict = field.build_widget_attrs(
            self.instance, {"content_type": "field"}
        )
        field_attrs: dict = field.build_field_attrs(
            {"widget": forms.HiddenInput(attrs=widget_attrs)}
        )
        return forms.CharField(**field_attrs)

    def prepare_captcha(self, field: Field):
        widget_attrs: dict = field.build_widget_attrs(
            self.instance, {"content_type": "field"}
        )
        field_attrs: dict = field.build_field_attrs(
            {"widget": ReCaptchaV2Checkbox(attrs=widget_attrs)}
        )
        return ReCaptchaField(**field_attrs)

    def prepare_upload_file(self, field: Field):
        message = (
            _("The file size is more than limit (limited size: %s bytes)")
            % field.file_size
        )
        widget_attrs: dict = field.build_widget_attrs(
            self.instance, {"multiple": True, "content_type": "field"}
        )
        field_attrs: dict = field.build_field_attrs(
            {
                "widget": forms.ClearableFileInput(attrs=widget_attrs),
                "validators": [
                    FileSizeValidator(field.file_size, message),
                    FileExtensionValidator(field.get_file_types()),
                ],
            }
        )
        return forms.FileField(**field_attrs)


class FormGeneratorForm(FormGeneratorBaseForm):
    def __init__(self, form, request, user_ip, *args, **kwargs):
        self.user_ip = user_ip
        self.request = request
        super().__init__(form, *args, **kwargs)

    def save(self):
        form_data = self.cleaned_data.copy()
        form_data.setdefault("request", self.request)
        save_module = fg_settings.FORM_RESPONSE_SAVE  
        save_module(self.instance, form_data, self.user_ip)# type: ignore


class FormGeneratorResponseForm(FormGeneratorBaseForm):
    def __init__(self, form, request, form_response, *args, **kwargs):
        super().__init__(form, *args, **kwargs)
        self.template_name_p = getattr(self.instance, "theme", self.template_name_p)
        self.request = request
        self.form_response = form_response
        form_response_data = form_response.get_data()
        for i, field in enumerate(self.instance.get_fields()):
            field_name = field.name
            method = f"prepare_{field.genre}"
            if hasattr(self, method):
                self.fields[field_name] = getattr(self, method)(field)
                if not form.is_editable:
                    self.fields[field_name].widget.attrs.update({"disabled": True})
                    if field.genre == const.FieldGenre.UPLOAD_FILE:
                        self.fields[f'{field_name}'] = getattr(self, 'prepare_upload_url_file')(field)
                try:
                    self.fields[field_name].initial = form_response_data[i].get(
                        "value", None
                    )

                except IndexError:
                    pass

    def prepare_upload_url_file(self, field: Field):
        widget_attrs: dict = field.build_widget_attrs(
            self.instance, {"content_type": "field"}
        )
        field_attrs: dict = field.build_field_attrs(
            {"widget": forms.URLInput(attrs=widget_attrs)}
        )
        field_attrs.update({'required': False, 'disabled': True})
        return forms.URLField(**field_attrs)


    def save(self):
        save_module = fg_settings.FORM_RESPONSE_SAVE
        form_data = self.form_response.pure_data
        for changed_data in self.changed_data:
            form_data[changed_data] = self.cleaned_data[changed_data]

        form_data.setdefault("request", self.request)
        save_module(self.instance, form_data, update_form_response_id=self.form_response.id)# type: ignore
        


class FieldForm(forms.ModelForm):
    class Meta:
        model = Field
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data["genre"] == const.FieldGenre.UPLOAD_FILE:
            if not cleaned_data["file_types"]:
                raise forms.ValidationError(
                    _("You should define FileTypes for upload file genre")
                )
        return cleaned_data

    def save(self, commit=True):
        if self.cleaned_data["genre"] == const.FieldGenre.UPLOAD_FILE and (
            not self.cleaned_data["file_size"] or self.cleaned_data["file_size"] <= 0
        ):
            self.instance.file_size = fg_settings.MAX_UPLOAD_FILE_SIZE
        return super().save(commit)


class FormAdminForm(forms.ModelForm):
    theme = forms.ChoiceField(choices=fg_settings.FORM_THEME_CHOICES.choices)  # type: ignore

    class Meta:
        model = Form
        fields = "__all__"
