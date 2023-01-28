from django import forms
from django.utils.translation import gettext as _

from captcha.fields import ReCaptchaField
from captcha.widgets import ReCaptchaV2Checkbox
from tempus_dominus.widgets import DatePicker, TimePicker, DateTimePicker

from django_form_generator.settings import form_generator_settings as fg_settings
from django_form_generator.models import Field, Form, Option, FieldValidator
from django_form_generator.fields import MultiInputWidgetField, MultiInputField, CustomeSelectFormField
from django_form_generator import const


class FormGeneratorBaseForm(forms.Form):
    def __init__(self, form, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance = form
        self.template_name_p = getattr(self.instance, "style", self.template_name_p)
        self._initial_fields()
        
    def _initial_fields(self):
        for field in self.instance.get_fields():
            method = f"prepare_{field.genre}"
            if hasattr(self, method):
                self.fields[field.name] = getattr(self, method)(self.instance, field)
                self._handel_required_fields(field, self.fields[field.name])

    def _handel_required_fields(self, field, form_field):
        if self.data and field.content_object:
            if isinstance(field.content_object, Option):
                field_name = self.instance.get_fields(extra={"id__in":
                                                field.content_object.fields.values_list('id', flat=True)}).last().name
                parent_data = self.data.get(field_name, '')
                if str(field.object_id) not in parent_data:
                    form_field.required = False
                else:
                    form_field.widget.attrs.update({'disabled': False})
            else:
                parent_data = self.data.get(field.content_object.name, '')
                if len(parent_data) <= 0:
                    form_field.required = False
                else:
                    form_field.widget.attrs.update({'disabled': False})

    def prepare_text_input(self, form: Form, field: Field):
        widget_attrs: dict = field.build_widget_attrs(
            form, {"content_type": "field"}
        )
        field_attrs: dict = field.build_field_attrs(
            {"widget": forms.TextInput(attrs=widget_attrs)}
        )
        return forms.CharField(**field_attrs)

    def prepare_multi_text_input(self, form: Form, field: Field):
        widget_attrs: dict = field.build_widget_attrs(
            form, {"content_type": "field", "multi-input": True}
        )
        field_attrs: dict = field.build_field_attrs(
            {"widget": MultiInputWidgetField(attrs=widget_attrs)}
        )
        return MultiInputField(**field_attrs)

    def prepare_text_area(self, form: Form, field: Field):
        widget_attrs: dict = field.build_widget_attrs(
            form, {"content_type": "field"}
        )
        field_attrs: dict = field.build_field_attrs(
            {"widget": forms.Textarea(attrs=widget_attrs)}
        )
        return forms.CharField(**field_attrs)

    def prepare_number(self, form: Form, field: Field):
        widget_attrs: dict = field.build_widget_attrs(
            form, {"content_type": "field"}
        )
        field_attrs: dict = field.build_field_attrs(
            {"widget": forms.NumberInput(attrs=widget_attrs)}
        )
        return forms.IntegerField(**field_attrs)

    def prepare_date(self, form: Form, field: Field):
        widget_attrs: dict = field.build_widget_attrs(
            form, {"content_type": "field"}
        )
        field_attrs: dict = field.build_field_attrs(
            {"widget": DatePicker(attrs=widget_attrs)}
        )
        return forms.DateField(**field_attrs)

    def prepare_time(self, form: Form, field: Field):
        widget_attrs: dict = field.build_widget_attrs(
            form, {"content_type": "field"}
        )
        field_attrs: dict = field.build_field_attrs(
            {"widget": TimePicker(attrs=widget_attrs)}
        )
        return forms.TimeField(**field_attrs)

    def prepare_datetime(self, form: Form, field: Field):
        widget_attrs: dict = field.build_widget_attrs(
            form, {"content_type": "field"}
        )
        field_attrs: dict = field.build_field_attrs(
            {"widget": DateTimePicker(attrs=widget_attrs)}
        )
        return forms.DateTimeField(**field_attrs)

    def prepare_email(self, form: Form, field: Field):
        widget_attrs: dict = field.build_widget_attrs(
            form, {"content_type": "field"}
        )
        field_attrs: dict = field.build_field_attrs(
            {"widget": forms.EmailInput(attrs=widget_attrs)}
        )
        return forms.EmailField(**field_attrs)

    def prepare_password(self, form: Form, field: Field):
        widget_attrs: dict = field.build_widget_attrs(
            form, {"content_type": "field"}
        )
        field_attrs: dict = field.build_field_attrs(
            {"widget": forms.PasswordInput(attrs=widget_attrs)}
        )
        return forms.CharField(**field_attrs)

    def prepare_checkbox(self, form: Form, field: Field):
        widget_attrs: dict = field.build_widget_attrs(
            form, {"content_type": "field"}
        )
        field_attrs: dict = field.build_field_attrs(
            {"widget": forms.CheckboxInput(attrs=widget_attrs)}
        )
        return forms.BooleanField(**field_attrs)

    def prepare_dropdown(self, form: Form, field: Field):
        widget_attrs: dict = field.build_widget_attrs(
            form, {"content_type": "option"}
        )
        choices = field.get_choices().values_list("id", "name")
        field_attrs: dict = field.build_field_attrs(
            {
                "widget": CustomeSelectFormField(attrs=widget_attrs),
                "choices": tuple(choices),
            }
        )
        return forms.ChoiceField(**field_attrs)

    def prepare_multi_checkbox(self, form: Form, field: Field):
        widget_attrs: dict = field.build_widget_attrs(
            form, {"content_type": "option"}
        )
        choices = field.get_choices().values_list("id", "name")
        field_attrs: dict = field.build_field_attrs(
            {
                "widget": forms.CheckboxSelectMultiple(attrs=widget_attrs),
                "choices": tuple(choices),
            }
        )
        return forms.MultipleChoiceField(**field_attrs)

    def prepare_radio(self, form: Form, field: Field):
        widget_attrs: dict = field.build_widget_attrs(
            form, {"content_type": "option"}
        )
        choices = field.get_choices().values_list("id", "name")
        field_attrs: dict = field.build_field_attrs(
            {"widget": forms.RadioSelect(attrs=widget_attrs), "choices": tuple(choices)}
        )
        return forms.ChoiceField(**field_attrs)

    def prepare_hidden(self, form: Form, field: Field):
        widget_attrs: dict = field.build_widget_attrs(
            form, {"content_type": "field"}
        )
        field_attrs: dict = field.build_field_attrs(
            {"widget": forms.HiddenInput(attrs=widget_attrs)}
        )
        return forms.CharField(**field_attrs)

    def prepare_captcha(self, form: Form, field: Field):
        widget_attrs: dict = field.build_widget_attrs(
            form, {"content_type": "field"}
        )
        field_attrs: dict = field.build_field_attrs(
            {"widget": ReCaptchaV2Checkbox(attrs=widget_attrs)}
        )
        return ReCaptchaField(**field_attrs)

    def prepare_upload_file(self, form: Form, field: Field):
        widget_attrs: dict = field.build_widget_attrs(
            form, {"multiple": True, "content_type": "field"}
        )
        field_attrs: dict = field.build_field_attrs(
            {
                "widget": forms.ClearableFileInput(attrs=widget_attrs),
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
        self.request = request
        self.form_response = form_response
        super().__init__(form, *args, **kwargs)

    def _initial_fields(self):
        form_response_data = self.form_response.get_data()
        for i, field in enumerate(self.form_response.form.get_fields()):
            field_name = field.name
            method = f"prepare_{field.genre}"
            if hasattr(self, method):
                self.fields[field_name] = getattr(self, method)(self.instance, field)
                try:
                    initial_value = form_response_data[i].get(
                        "value", None
                    )
                    if (not initial_value and isinstance(initial_value, (list, tuple))) or field.write_only:
                        initial_value = None
                    self.fields[field_name].initial = initial_value
                    if initial_value:
                        try:
                            del self.fields[field_name].widget.attrs["disabled"]
                        except KeyError:
                            pass
                except IndexError:
                    pass
                
                if not self.instance.is_editable:
                    self.fields[field_name].widget.attrs.update({"disabled": True})
                
                self._handel_required_fields(field, self.fields[field.name])

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
        if 'genre' in cleaned_data and cleaned_data["genre"] == const.FieldGenre.UPLOAD_FILE:
            data = [val for key, val in self.data.items() if key.startswith('validators') and key.endswith('validator') and val]
            if const.Validator.FILE_EXTENTION.value not in data or const.Validator.FILE_SIZE.value not in data:
                raise forms.ValidationError(
                    _("You should define FileExtention and FileSize validators for upload file genre")
                )
        return cleaned_data

class FormAdminForm(forms.ModelForm):
    style = forms.ChoiceField(choices=fg_settings.FORM_STYLE_CHOICES.choices)  # type: ignore

    class Meta:
        model = Form
        fields = "__all__"


class ValidatorAdminForm(forms.ModelForm):

    class Meta:
        model = FieldValidator
        fields = '__all__'

    def clean_value(self):
        value = self.cleaned_data['value']
        if value:
            const.Validator(self.cleaned_data['validator']).clean(value)
        return value

class FormResponseFilterForm(forms.Form):
    operand = forms.ChoiceField(choices=(('OR', 'OR'), ('AND', 'AND')),  required=False)
    field = forms.ModelChoiceField(Field.objects.all(), required=False, widget=forms.widgets.Select(attrs={'onchange': 'valueField(event)'}))
    field_lookup = forms.ChoiceField(choices=const.FieldLookupType.choices,  required=False,
         widget=forms.widgets.Select(attrs={'onchange': 'typeField(event)'}))
    value = forms.CharField(max_length=120, required=False)