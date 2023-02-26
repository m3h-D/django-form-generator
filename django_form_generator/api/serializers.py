from django.core.validators import FileExtensionValidator
from django.utils.translation import gettext as _
from rest_framework import serializers
from django_form_generator.common.utils import FileSizeValidator
from django_form_generator.models import Form, Option, Field
from django_form_generator.settings import form_generator_settings as fg_settings
from drf_recaptcha.fields import ReCaptchaV3Field

class CustomMultipleChoiceField(serializers.MultipleChoiceField):

    def to_internal_value(self, data):
        return list(super().to_internal_value(data))


class FormSerializer(serializers.ModelSerializer):

    class Meta:
        model = Form
        fields = ['id', 'title', 'slug', 'status']


class FormFullSerializer(serializers.ModelSerializer):
    form_fields = serializers.SerializerMethodField()
    
    class Meta:
        model = Form
        fields = ['title', 'slug', 'status', 'submit_text', 'redirect_url', 'success_message', 'style', 'direction', 'limit_to', 'valid_from', 'valid_to', 'is_editable', 'form_fields']

    def get_form_fields(self, obj):
        return obj.render_fields


class BaseFormSerializer(serializers.Serializer):

    def __init__(self, instance=None, data=None, **kwargs):
        super().__init__(instance, data, **kwargs)
        self._initial_fields()


    def _initial_fields(self):
        if self.form:
            for field in self.form.get_fields():
                method = f"prepare_{field.genre}"
                if hasattr(self, method):
                    self.fields[field.name] = getattr(self, method)(field)
                self._handel_required_fields(field, self.fields[field.name])

    def _handel_required_fields(self, field: Field, form_field):
        if self.initial_data and field.content_object:
            if isinstance(field.content_object, Option):
                field_name = self.form.get_fields(extra={"id__in":field.content_object.fields.values_list('id', flat=True)}).last().name
                parent_data = self.initial_data.get(field_name, '')
                if (isinstance(parent_data, list) and field.object_id not in parent_data) or (field.object_id == parent_data):
                    form_field.allow_null = True
                else:
                    form_field.read_only = False
            else:
                parent_data = self.initial_data.get(field.content_object.name, '')
                if len(parent_data) <= 0:
                    form_field.allow_null = True
                else:
                    form_field.read_only = False
    
    def prepare_text_input(self, field: Field):
        field_attrs: dict = field.build_serializer_attrs()
        return serializers.CharField(**field_attrs)

    def prepare_text_area(self, field: Field):
        field_attrs: dict = field.build_serializer_attrs()
        return serializers.CharField(**field_attrs)

    def prepare_number(self, field: Field):
        field_attrs: dict = field.build_serializer_attrs()
        return serializers.IntegerField(**field_attrs)

    def prepare_date(self, field: Field):
        field_attrs: dict = field.build_serializer_attrs()
        return serializers.DateField(**field_attrs)

    def prepare_time(self, field: Field):
        field_attrs: dict = field.build_serializer_attrs()
        return serializers.TimeField(**field_attrs)

    def prepare_datetime(self, field: Field):
        field_attrs: dict = field.build_serializer_attrs()
        return serializers.DateTimeField(**field_attrs)

    def prepare_email(self, field: Field):
        field_attrs: dict = field.build_serializer_attrs()
        return serializers.EmailField(**field_attrs)

    def prepare_password(self, field: Field):
        field_attrs: dict = field.build_serializer_attrs()
        return serializers.CharField(**field_attrs)

    def prepare_checkbox(self, field: Field):
        field_attrs: dict = field.build_serializer_attrs()
        return serializers.BooleanField(**field_attrs)

    def prepare_dropdown(self, field: Field):
        choices = field.get_choices().values_list("id", "name")
        field_attrs: dict = field.build_serializer_attrs()
        return serializers.ChoiceField(choices=choices, **field_attrs)

    def prepare_multi_checkbox(self, field: Field):
        choices = field.get_choices().values_list("id", "name")
        field_attrs: dict = field.build_serializer_attrs()
        return CustomMultipleChoiceField(choices=choices, **field_attrs)

    def prepare_radio(self, field: Field):
        choices = field.get_choices().values_list("id", "name")
        field_attrs: dict = field.build_serializer_attrs()
        return serializers.ChoiceField(choices=choices, **field_attrs)

    def prepare_hidden(self, field: Field):
        field_attrs: dict = field.build_serializer_attrs()
        field_attrs.update({'default': field_attrs.get('initial', None)})
        return serializers.HiddenField(**field_attrs)

    def prepare_captcha(self, field: Field):
        field_attrs: dict = field.build_serializer_attrs()
        return ReCaptchaV3Field(**field_attrs)

    def prepare_upload_file(self, field: Field):
        message = (
            _("The file size is more than limit (limited size: %s bytes)")
            % field.file_size
        )
        field_attrs: dict = field.build_serializer_attrs()
        validators = [FileSizeValidator(field.file_size, message),
                    FileExtensionValidator(field.get_file_types()),]
        return serializers.FileField(validators=validators, **field_attrs)


class FormGeneratorSerializer(BaseFormSerializer):

    # form = serializers.SerializerMethodField()

    # def get_form(self, obj):
    #     return FormFullSerializer(self.form)

    def __init__(self, instance=None, data=None, *args, **kwargs):
        serializers.Serializer.__init__(self, instance, data, *args, **kwargs)
        self.form = self.context.get('form')
        self.request = self.context.get('request')
        self.user_ip = self.context.get('user_ip')
        self._initial_fields()


    def save(self):
        form_data = self.validated_data
        form_data.setdefault("request", self.request)
        save_module = fg_settings.FORM_RESPONSE_SAVE  
        save_module(self.form, form_data, self.user_ip)# type: ignore

class FormGeneratorResponseSerializer(BaseFormSerializer):
    def __init__(self, instance=None, data=None, *args, **kwargs):
        serializers.Serializer.__init__(self, instance, data, *args, **kwargs)
        self.form = self.context['form']
        self.request = self.context['request']
        self.form_response = self.context['form_response']
        self._initial_fields()

    @property
    def output_data(self):
        fields = self.form.render_fields.copy()
        for i, field in enumerate(fields):
            if field['attrs']['write_only']:
                fields.pop(i)
                i -= 1
            field.update({'value': self.form_response.get_data()[i]['value']})
        return fields

    def _initial_fields(self):
        form_response_data = self.form_response.get_data()
        for i, field in enumerate(self.form.get_fields()):
            field_name = field.name
            method = f"prepare_{field.genre}"
            if hasattr(self, method):
                self.fields[field_name] = getattr(self, method)(field)
                if not self.form.is_editable:
                    self.fields[field_name].read_only = True
                try:
                    initial_value = form_response_data[i].get(
                        "value", None
                    )
                    self.fields[field_name].initial = initial_value
                    if initial_value:
                        try:
                            self.fields[field_name].read_only = False
                        except KeyError:
                            pass
                except IndexError:
                    pass
                
                self._handel_required_fields(field, self.fields[field.name])

    def save(self, **kwargs):
        save_module = fg_settings.FORM_RESPONSE_SAVE
        form_data = self.form_response.pure_data
        for changed_data in self.validated_data.keys():
            form_data[changed_data] = self.validated_data[changed_data]

        form_data.setdefault("request", self.request)
        return save_module(self.form, form_data, update_form_response_id=self.form_response.id)# type: ignore

