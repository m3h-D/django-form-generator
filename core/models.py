import pathlib
from sys import platform
from django.db import models
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.fields import GenericForeignKey
from django.core.mail import EmailMessage
from django.conf import settings
from django.core.cache import cache


from common.models import BaseModel
from common.utils import APICall, evaluate_data

from core import consts
from core.managers import FormDetailManager

CONTENT_TYPE_MODELS_LIMIT = models.Q(app_label='core', model='field') | \
                            models.Q(app_label='core', model='value')


class FieldCategory(BaseModel):
    title = models.CharField(_("Title"), max_length=200)
    is_active = models.BooleanField(_("Is Active"), default=True)
    parent = models.ForeignKey("self", verbose_name=_("Parent Category"), on_delete=models.CASCADE,
                               blank=True, null=True, limit_choices_to={'is_active': True}, related_name='children')
    weight = models.PositiveIntegerField(_("Weight"))

    class Meta:
        verbose_name = _("FieldCategory")
        verbose_name_plural = _("FieldCategories")
        ordering = ('weight',)
        indexes = [
            models.Index(fields=("title", ), name='%(app_label)s.%(class)s_title'),
            models.Index(fields=("is_active", ),
                         name='%(app_label)s.%(class)s_active'),
            models.Index(fields=("weight", ),
                         name='%(app_label)s.%(class)s_weight'),
        ]

    def __str__(self) -> str:
        return self.title


class Form(BaseModel):
    title = models.CharField(_("Title"), max_length=200)
    slug = models.SlugField(_("Slug"), unique=True, allow_unicode=True)
    status = models.CharField(_("Status"), max_length=50,
                              choices=consts.FormStatus.choices, default=consts.FormStatus.DRAFT)
    fields = models.ManyToManyField("core.Field", verbose_name=_(
        "Fields"), through='core.FormFieldThrough', related_name='forms')
    apis = models.ManyToManyField("core.FormAPIManager", verbose_name=_(
        "Apis"), through='core.FormAPIThrough', related_name='forms')

    class Meta:
        verbose_name = _("Form")
        verbose_name_plural = _("Forms")

        indexes = [
            models.Index(fields=("title", ), name='%(app_label)s.%(class)s_title'),
            models.Index(fields=("slug", ), name='%(app_label)s.%(class)s_slug'),
            models.Index(fields=("status", ), name='%(app_label)s.%(class)s_status')
        ]

    def __str__(self) -> str:
        return self.title

    def call_post_apis(self, response_data=None):
        #TODO: make it background task
        cache_ = cache.get(f'Form_APIs_{self.pk}_post')
        if cache_:
            return cache_
        responses = []
        for api in self.apis.filter(is_active=True,
                                    execute_time=consts.FormAPIManagerExecuteTime.POST_LOAD): 
            api: FormAPIManager
            response = APICall(api.method.lower(), api.url, api.body, response_data, headers=api.headers)
            status_code, result = response.get_result()
            responses.append((api, status_code, result))
        cache.set(f'Form_APIs_{self.pk}_post', responses)
        return responses

    def render_post_apis(self, response_data=None):
        data = []
        results = self.call_post_apis(response_data)
        for api, _, result in results:
            api: FormAPIManager
            if api.show_result:
                res = evaluate_data(api.response, result)
                data.append(res)
        return data

    def call_pre_apis(self, response_data=None):
        #TODO: make it background task
        cache_ = cache.get(f'Form_APIs_{self.pk}_pre')
        if cache_:
            return cache_
        responses = []
        for api in self.apis.filter(is_active=True,
                                    execute_time=consts.FormAPIManagerExecuteTime.PRE_LOAD): 
            api: FormAPIManager
            response = APICall(api.method.lower(), api.url, api.body, response_data, headers=api.headers)
            status_code, result = response.get_result()
            responses.append((api, status_code, result))
        cache.set(f'Form_APIs_{self.pk}_pre', responses)
        return responses

        
    def render_pre_apis(self, response_data=None):
        data = []
        results = self.call_pre_apis(response_data)
        for api, _, result in results:
            api: FormAPIManager
            if api.show_result:
                res = evaluate_data(api.response, result)
                data.append((api.pk, res))
        return data

    def get_fields(self):
        return self.fields.filter(is_active=True).order_by('category__weight', 'form_field_through__id')
            


class FormDetail(BaseModel):
    form = models.OneToOneField(
        "core.Form", verbose_name=_("Form"), on_delete=models.CASCADE, related_name='detail')
    submit_text = models.CharField(
        _("Submit Text"), max_length=100, default=_('Submit'))
    redirect_url = models.URLField(
        _("Redirect URL"), max_length=200, blank=True, null=True)
    success_message = models.CharField(_("Success Message"), max_length=255)
    template = models.ForeignKey("core.FormTemplate", verbose_name=_(
        "Template"), on_delete=models.SET_NULL, blank=True, null=True, related_name='forms', limit_choices_to={'is_active': True})
    send_mail = models.BooleanField(_("Send E-mail"), default=False)
    mail_seubject = models.CharField(
        _("Mail Subject"), max_length=200, blank=True, null=True)
    mail_to = models.CharField(
        _("Mail To"), max_length=500, blank=True, null=True)
    mail_bcc = models.CharField(
        _("Mail BCC"), max_length=500, blank=True, null=True)
    mail_message = models.TextField(_("Mail Message"), blank=True, null=True, help_text=_(
        'You can use form fields name in this box eg: {{field_name}} or {{form_data}} to send all user data'))
    limit_to = models.PositiveIntegerField(_("Limit Submiting Form"), blank=True, null=True)
    valid_from = models.DateTimeField(_("Valid From"), blank=True, null=True)
    valid_to = models.DateTimeField(_("Valid To"), blank=True, null=True)

    objects = FormDetailManager()

    class Meta:
        verbose_name = _("Form Detail")
        verbose_name_plural = _("Form Details")

    def __str__(self) -> str:
        return str(self.form)

    def send_email(self, response_data=None):
        #TODO: make it background task
        if response_data is not None:
            data_ = evaluate_data(self.mail_message, response_data)
            self.content = ' '.join(data_) if isinstance(data_, list) else data_
        email = EmailMessage(self.mail_seubject,
                            self.mail_message,
                            settings.EMAIL_FROM,
                            self.mail_to.split(','),
                            self.mail_bcc.split(','))
        return email.send()


class FormFieldThrough(models.Model):
    form = models.ForeignKey("core.Form", verbose_name=_(
        "Form"), on_delete=models.CASCADE, related_name='form_field_through')
    field = models.ForeignKey("core.Field", verbose_name=_(
        "Field"), on_delete=models.CASCADE, related_name='form_field_through')

    def __str__(self) -> str:
        return f'{self.form.title} | {self.field.name}'


class Field(BaseModel):
    label = models.CharField(_("Label"), max_length=100)
    name = models.CharField(_("Name"), max_length=100, blank=True, unique=True)
    genre = models.CharField(_("Genre"), max_length=80,
                             choices=consts.FieldGenre.choices)
    is_required = models.BooleanField(_("Is Required"), default=True)
    placeholder = models.CharField(
        _("Placeholder"), max_length=100, blank=True, null=True)
    default = models.CharField(
        _("Default Value"), max_length=255, blank=True, null=True)
    help_text = models.CharField(
        _("Help Text"), max_length=200, blank=True, null=True)
    regex_pattern = models.CharField(
        _("Regex Pattern"), max_length=500, blank=True, null=True)
    error_message = models.CharField(
        _("Error Message"), max_length=200, blank=True, null=True)
    category = models.ForeignKey("core.FieldCategory", verbose_name=_("Category"), on_delete=models.SET_NULL, blank=True, null=True,
                                 limit_choices_to={'is_active': True})
    weight = models.PositiveIntegerField(_("Weight"))
    values = models.ManyToManyField("core.Value", through='core.FieldValueThrough', verbose_name=_(
        "Values"), related_name='fields', help_text=_("Only for multi value fields like Dropdown, Radio, Checkbox, etc..."))
    is_active = models.BooleanField(_("Is Active"))
    # file
    file_types = models.CharField(_("Allow File Types"), max_length=100, blank=True, null=True)
    file_size = models.IntegerField(_("File Size"), blank=True, null=True)
    # depends
    content_type = models.ForeignKey("contenttypes.ContentType", verbose_name=_(
        "Depends On Object"), on_delete=models.SET_NULL, related_name='fields', limit_choices_to=CONTENT_TYPE_MODELS_LIMIT, blank=True, null=True)
    object_id = models.BigIntegerField(_("Depends on Object ID"), blank=True, null=True)
    content_object = GenericForeignKey()

    class Meta:
        verbose_name = _("Field")
        verbose_name_plural = _("Fields")
        ordering = ('weight',)
        indexes = [
            models.Index(fields=("label", ), name='%(app_label)s.%(class)s_label'),
            models.Index(fields=("name", ), name='%(app_label)s.%(class)s_name'),
            models.Index(fields=("genre", ), name='%(app_label)s.%(class)s_genre'),
            models.Index(fields=("weight", ),
                         name='%(app_label)s.%(class)s_weight')
        ]

    def __str__(self) -> str:
        return self.label

    def build_field_attrs(self, extra_attrs: dict|None=None):
        attrs = {'required': self.is_required,
                 'help_text': self.help_text,
                 'label': self.label}

        if self.content_object is not None:
            attrs.update({'disabled': True})

        if self.error_message:
            attrs.update({'error_messages': {'Invalid': self.error_message}})

        if self.regex_pattern is not None:
            attrs.update({'validators': [RegexValidator(
                self.regex_pattern, self.error_message or None)]})

        if self.default is not None:
            attrs.update({'initial': self.default})

        if extra_attrs:
            attrs.update(extra_attrs)
        return attrs

    def build_widget_attrs(self, extra_attrs: dict|None=None):
        attrs = {'instance_id': self.pk}

        if self.content_object is not None:
            attrs.update({'parent_object_id': self.object_id,
                        'parent_content_type': self.content_type.model})
        else:
            attrs.update({'onchange': 'onElementChange(this)'})

        if self.category is not None:
            attrs.update({'category': self.category.title})

        if self.placeholder is not None:
            attrs.update({'placeholder': self.placeholder})
        if extra_attrs:
            attrs.update(extra_attrs)
        return attrs

    def get_choices(self):
        return self.values.filter(is_active=True)

    def get_file_types(self):
        return self.file_types.replace(' ', ',').replace(', ', ',').split(',')


class FieldValueThrough(models.Model):
    field = models.ForeignKey("core.Field", verbose_name=_(
        "Field"), on_delete=models.CASCADE, related_name='field_values')
    value = models.ForeignKey("core.Value", verbose_name=_(
        "Value"), on_delete=models.CASCADE, related_name='field_values')

    def __str__(self) -> str:
        return f'{self.field.name} | {self.value.name}'


class Value(BaseModel):
    name = models.CharField(_("Name"), max_length=100)
    is_active = models.BooleanField(_("Is Active"), default=True)
    weight = models.PositiveIntegerField(_("Weight"))

    class Meta:
        verbose_name = _("Value")
        verbose_name_plural = _("Values")
        ordering = ('weight',)
        indexes = [
            models.Index(fields=("name", ), name='%(app_label)s.%(class)s_name'),
            models.Index(fields=("weight", ),
                         name='%(app_label)s.%(class)s_weight')
        ]

    def __str__(self) -> str:
        return self.name


class FormTemplate(BaseModel):
    title = models.CharField(_("Title"), max_length=200)
    is_active = models.BooleanField(_("Is Active"), default=True)
    directory = models.CharField(_("Directory"), max_length=500)

    class Meta:
        verbose_name = _("FormTemplate")
        verbose_name_plural = _("FormTemplates")

    def __str__(self) -> str:
        return self.title

    @property
    def get_directory(self):
        if not platform.startswith("linux"):
            parts = pathlib.PurePath(self.directory).parts
            index = parts.index('templates')
            return '/'.join(parts[index+1:])
        return self.directory

class FormAPIThrough(models.Model):
    form = models.ForeignKey("core.Form", verbose_name=_(
        "Form"), on_delete=models.CASCADE, related_name='form_apis')
    api = models.ForeignKey("core.FormAPIManager", verbose_name=_(
        "API"), on_delete=models.CASCADE, related_name='form_apis')

    def __str__(self) -> str:
        return f'{self.form.title} | {self.api.title}'


class FormAPIManager(BaseModel):
    title = models.CharField(_("Title"), max_length=200)
    url = models.URLField(_("URL"), max_length=200)
    headers = models.JSONField(_("Headers"), blank=True, null=True)
    method = models.CharField(
        _("Method"), max_length=50, choices=consts.FormAPIManagerMethod.choices)
    body = models.TextField(_("Body"), blank=True, null=True)
    execute_time = models.CharField(
        _("Execute Time"), max_length=50, choices=consts.FormAPIManagerExecuteTime.choices)
    response = models.TextField(_("Response"), blank=True, null=True)
    is_active = models.BooleanField(_("Is Active"))
    show_result = models.BooleanField(_("Show Result"), default=False)
    weight = models.PositiveIntegerField(_("Weight"))

    class Meta:
        verbose_name = _("FormAPIManager")
        verbose_name_plural = _("FormAPIManagers")
        ordering = ('weight',)
        indexes = [
            models.Index(fields=("title", ), name='%(app_label)s.%(class)s_title'),
            models.Index(fields=("method", ),
                         name='%(app_label)s.%(class)s_method'),
            models.Index(fields=("is_active", ),
                         name='%(app_label)s.%(class)s_active'),
            models.Index(fields=("weight", ),
                         name='%(app_label)s.%(class)s_weight')
        ]

    def __str__(self) -> str:
        return self.title


class FormResponse(BaseModel):
    form = models.ForeignKey("core.Form", verbose_name=_("Form"), on_delete=models.PROTECT, related_name='responses')
    data = models.JSONField(_("Data"))
    api_response = models.JSONField(_("Api Respons"), blank=True, null=True)
    user_ip = models.GenericIPAddressField(_('IP Address'))

    class Meta:
        verbose_name = _('Form Response')
        verbose_name_plural = _('Form Responses')
        indexes = [
            models.Index(fields=('user_ip',), name='%(app_label)s.%(class)s_user'),
        ]

    def __str__(self):
        return self.form.title

    @property
    def pure_data(self):
        """self.data sample:
            [{
                "id": 1,
                "name": "field_name",
                "label": "field_label",
                "genre": "text_input",
                "value": "User input data"
            }]
        """
        result = {}
        for d in self.data:
            result[d['name']] = d['value'] #* {field_name: User input data}
        return result
