import pathlib
from unittest import result
from django.db import models
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.fields import GenericForeignKey
from django.core.cache import cache
from django.conf import settings

from form_generator.common.models import BaseModel
from form_generator.common.utils import APICall, evaluate_data, upload_file_handler

from form_generator import const
from form_generator.managers import FormManager


CONTENT_TYPE_MODELS_LIMIT = models.Q(app_label='form_generator', model='field') | \
                            models.Q(app_label='form_generator', model='value')


class FieldCategory(BaseModel):
    title = models.CharField(_("Title"), max_length=200, unique=True)
    is_active = models.BooleanField(_("Is Active"), default=True)
    parent = models.ForeignKey("self", verbose_name=_("Parent Category"), on_delete=models.CASCADE,
                               blank=True, null=True, limit_choices_to={'is_active': True}, related_name='children')
    weight = models.PositiveIntegerField(_("Weight"))

    class Meta:
        verbose_name = _("FieldCategory")
        verbose_name_plural = _("FieldCategories")
        ordering = ('weight',)
        indexes = [
            models.Index(fields=("title", ), name='f_g_%(class)s_title'),
            models.Index(fields=("is_active", ),
                         name='f_g_%(class)s_active'),
            models.Index(fields=("weight", ),
                         name='f_g_%(class)s_weight'),
        ]

    def __str__(self) -> str:
        return self.title

    def get_fields(self):
        return self.fields.filter(is_active=True) #type: ignore


class Form(BaseModel):
    title = models.CharField(_("Title"), max_length=200)
    slug = models.SlugField(_("Slug"), unique=True, allow_unicode=True)
    status = models.CharField(_("Status"), max_length=50,
                              choices=const.FormStatus.choices, default=const.FormStatus.DRAFT)
    submit_text = models.CharField(
        _("Submit Text"), max_length=100, default=_('Submit'))
    redirect_url = models.URLField(
        _("Redirect URL"), max_length=200, blank=True, null=True)
    success_message = models.CharField(_("Success Message"), max_length=255, blank=True, null=True)
    theme = models.FilePathField(_("Theme"), path=str(settings.BASE_DIR / 'form_generator/templates/form_generator/fields/'), 
        recursive=True, max_length=250, help_text=_('If choose dynamic_fields.html the order of fields depends on position of Field.'))
    direction = models.CharField(_("Direction"), max_length=3, choices=const.FormDirection.choices, default=const.FormDirection.LTR)
    limit_to = models.PositiveIntegerField(_("Limit Submiting Form"), blank=True, null=True)
    valid_from = models.DateTimeField(_("Valid From"), blank=True, null=True)
    valid_to = models.DateTimeField(_("Valid To"), blank=True, null=True)
    fields = models.ManyToManyField("form_generator.Field", verbose_name=_(
        "Fields"), through='form_generator.FormFieldThrough', related_name='forms')
    apis = models.ManyToManyField("form_generator.FormAPIManager", verbose_name=_(
        "Apis"), through='form_generator.FormAPIThrough', related_name='forms')

    objects: FormManager = FormManager()

    class Meta:
        verbose_name = _("Form")
        verbose_name_plural = _("Forms")

        indexes = [
            models.Index(fields=("title", ), name='f_g_%(class)s_title'),
            models.Index(fields=("slug", ), name='f_g_%(class)s_slug'),
            models.Index(fields=("status", ), name='f_g_%(class)s_status')
        ]

    def __str__(self) -> str:
        return self.title

    def __call_apis(self, execute_time: const.FormAPIManagerExecuteTime, response_data: dict):
        cache_key = f"FormAPIs_{self.pk}_{execute_time}_{response_data['request'].session.session_key}"
        cached_response = cache.get(cache_key)
        if cached_response: return cached_response

        responses = []
        for api in self.apis.filter(is_active=True,
                                    execute_time=execute_time): 
            api: FormAPIManager
            response = APICall(api.method.lower(), api.url, api.body, response_data, headers=api.headers)
            status_code, result = response.get_result()
            responses.append((api, status_code, result))
        cache.set(cache_key, responses)
        return responses


    def call_post_apis(self, response_data: dict):
        return self.__call_apis(const.FormAPIManagerExecuteTime.POST_LOAD, response_data)

    def render_post_apis(self, response_data: dict):
        data = []
        results = self.call_post_apis(response_data)
        for api, _, result in results:
            res = evaluate_data(api.response, result)
            data.append(res)
        return data

    def call_pre_apis(self, response_data: dict):
        return self.__call_apis(const.FormAPIManagerExecuteTime.PRE_LOAD, response_data)

        
    def render_pre_apis(self, response_data: dict):
        data = []
        results = self.call_pre_apis(response_data)
        for api, _, result in results:
            res = evaluate_data(api.response, result)
            data.append((api.pk, res))
        return data

    def get_fields(self):
        return self.fields.filter(is_active=True).order_by(models.F('form_field_through__category__weight').asc(nulls_last=True), 
                                                                    'form_field_through__weight')

    def save_response(self, data, user_ip):
        api_response = []
        pre_result = self.call_pre_apis(data)
        post_result = self.call_post_apis(data)
        pre = self._generate_api_result(pre_result)
        post = self._generate_api_result(post_result)
        if pre:
            api_response.append(pre)
        if post:
            api_response.append(post)
        response = FormResponse.objects.create(data=self._generate_data(data), 
                                    user_ip=user_ip, 
                                    api_response=api_response or None, 
                                    form=self)
        return response
    
    def _generate_api_result(self, results):
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
        return data or None


    def _generate_data(self, form_data):
        data = []
        request = form_data['request']
        for field in self.get_fields():
            field_value = form_data[field.name]
            if field.genre == const.FieldGenre.CAPTCHA:
                continue
            category_title = None
            category = field.form_field_through.filter(form_id=self.pk).last().category
            if category:
                category_title = category.title
            if field.genre == const.FieldGenre.UPLOAD_FILE and field_value is not None:
                form_data[field.name] = field.upload_file(request._current_scheme_host, field_value)

            data.append(
                {
                    "id": field.id,
                    "name": field.name,
                    "label": field.label,
                    "genre": field.genre,
                    "category": category_title,
                    "value": form_data[field.name]
                }
            )
        return data or None



class FormFieldThrough(models.Model):
    form = models.ForeignKey("form_generator.Form", verbose_name=_(
        "Form"), on_delete=models.CASCADE, related_name='form_field_through')
    field = models.ForeignKey("form_generator.Field", verbose_name=_(
        "Field"), on_delete=models.CASCADE, related_name='form_field_through')
    position = models.CharField(_("Position"), max_length=100, choices=const.FieldPosition.choices, default=const.FieldPosition.BREAK)
    category = models.ForeignKey("form_generator.FieldCategory", verbose_name=_("Category"), on_delete=models.SET_NULL, blank=True, null=True,
                                 limit_choices_to={'is_active': True}, related_name='form_field_through')
    weight = models.PositiveIntegerField(_("Weight"))

    class Meta:
        ordering = ('weight',)
        indexes = [
            models.Index(fields=("weight", ), name='f_g_%(class)s_weight'),
        ]

    def __str__(self) -> str:
        return f'{self.form.title} | {self.field.name}'


class Field(BaseModel):
    label = models.CharField(_("Label"), max_length=100)
    name = models.CharField(_("Name"), max_length=100, blank=True, unique=True)
    genre = models.CharField(_("Genre"), max_length=80,
                             choices=const.FieldGenre.choices)
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
    values = models.ManyToManyField("form_generator.Value", through='form_generator.FieldValueThrough', verbose_name=_(
        "Values"), related_name='fields', help_text=_("Only for multi value fields like Dropdown, Radio, Checkbox, etc..."))
    is_active = models.BooleanField(_("Is Active"))
    # file
    file_types = models.CharField(_("Allow File Types"), max_length=100, blank=True, null=True, help_text=_('example: jpg,png'))
    file_size = models.IntegerField(_("File Size"), blank=True, null=True, help_text=_('Default value will be set to 50 MB'))
    # depends
    content_type = models.ForeignKey("contenttypes.ContentType", verbose_name=_(
        "Depends On Object"), on_delete=models.SET_NULL, related_name='fields', limit_choices_to=CONTENT_TYPE_MODELS_LIMIT, blank=True, null=True)
    object_id = models.BigIntegerField(_("Depends on Object ID"), blank=True, null=True)
    content_object = GenericForeignKey()

    class Meta:
        verbose_name = _("Field")
        verbose_name_plural = _("Fields")
        indexes = [
            models.Index(fields=("label", ), name='f_g_%(class)s_label'),
            models.Index(fields=("name", ), name='f_g_%(class)s_name'),
            models.Index(fields=("genre", ), name='f_g_%(class)s_genre'),
        ]

    def __str__(self) -> str:
        return self.label

    def build_field_attrs(self, extra_attrs: dict|None=None):
        attrs = {'required': self.is_required,
                 'help_text': self.help_text,
                 'label': self.label}

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

    def build_widget_attrs(self, form, extra_attrs: dict|None=None):
        attrs = {'instance_id': self.pk, 'onchange': 'onElementChange(this)'}
        form_field_through = self.form_field_through.filter(form_id=form.id).last() #type: ignore

        if self.content_object is not None:
            attrs.update({'disabled': True})
            
        if self.content_object is not None:
            attrs.update({'parent_object_id': self.object_id,
                        'parent_content_type': self.content_type.model})

        if form_field_through.category is not None:
            attrs.update({'category': form_field_through.category.title})

        if self.placeholder is not None:
            attrs.update({'placeholder': self.placeholder})

        attrs.update({'position': form_field_through.position})


        if extra_attrs:
            attrs.update(extra_attrs)
        return attrs

    def get_choices(self):
        return self.values.filter(is_active=True).order_by('field_values__weight')

    def get_file_types(self):
        return self.file_types.replace(' ', ',').replace(', ', ',').split(',')

    def upload_file(self, host, data):
        directory =  upload_file_handler(data)
        parts = pathlib.Path(directory).parts
        return {'directory_path': directory,
                'url_path': host + settings.MEDIA_URL  + '/'.join(parts[-2:])}



class FieldValueThrough(models.Model):
    field = models.ForeignKey("form_generator.Field", verbose_name=_(
        "Field"), on_delete=models.CASCADE, related_name='field_values')
    value = models.ForeignKey("form_generator.Value", verbose_name=_(
        "Value"), on_delete=models.CASCADE, related_name='field_values')
    weight = models.PositiveIntegerField(_("Weight"))

    class Meta:
        ordering = ('weight',)
        indexes = [
            models.Index(fields=("weight", ),
                         name='f_g_%(class)s_weight')
        ]

    def __str__(self) -> str:
        return f'{self.field.name} | {self.value.name}'


class Value(BaseModel):
    name = models.CharField(_("Name"), max_length=100)
    is_active = models.BooleanField(_("Is Active"), default=True)

    class Meta:
        verbose_name = _("Value")
        verbose_name_plural = _("Values")
        indexes = [
            models.Index(fields=("name", ), name='f_g_%(class)s_name'),
        ]

    def __str__(self) -> str:
        return self.name


class FormAPIThrough(models.Model):
    form = models.ForeignKey("form_generator.Form", verbose_name=_(
        "Form"), on_delete=models.CASCADE, related_name='form_apis')
    api = models.ForeignKey("form_generator.FormAPIManager", verbose_name=_(
        "API"), on_delete=models.CASCADE, related_name='form_apis')
    weight = models.PositiveIntegerField(_("Weight"))

    class Meta:
        ordering = ('weight',)
        indexes = [
            models.Index(fields=("weight", ),
                         name='f_g_%(class)s_weight')
        ]
    

    def __str__(self) -> str:
        return f'{self.form.title} | {self.api.title}'


class FormAPIManager(BaseModel):
    title = models.CharField(_("Title"), max_length=200)
    url = models.URLField(_("URL"), max_length=200)
    headers = models.JSONField(_("Headers"), blank=True, null=True)
    method = models.CharField(
        _("Method"), max_length=50, choices=const.FormAPIManagerMethod.choices)
    body = models.TextField(_("Body"), blank=True, null=True)
    execute_time = models.CharField(
        _("Execute Time"), max_length=50, choices=const.FormAPIManagerExecuteTime.choices)
    response = models.TextField(_("Response"), blank=True, null=True)
    is_active = models.BooleanField(_("Is Active"))

    class Meta:
        verbose_name = _("FormAPIManager")
        verbose_name_plural = _("FormAPIManagers")
        indexes = [
            models.Index(fields=("title", ), name='f_g_%(class)s_title'),
            models.Index(fields=("method", ),
                         name='f_g_%(class)s_method'),
            models.Index(fields=("is_active", ),
                         name='f_g_%(class)s_active'),
        ]

    def __str__(self) -> str:
        return self.title


class FormResponse(BaseModel):
    form = models.ForeignKey("form_generator.Form", verbose_name=_("Form"), on_delete=models.PROTECT, related_name='responses')
    data = models.JSONField(_("Data"))
    api_response = models.JSONField(_("Api Respons"), blank=True, null=True)
    user_ip = models.GenericIPAddressField(_('IP Address'))

    class Meta:
        verbose_name = _('Form Response')
        verbose_name_plural = _('Form Responses')
        indexes = [
            models.Index(fields=('user_ip',), name='f_g_%(class)s_user'),
        ]

    def __str__(self):
        return self.form.title

    @property
    def pure_data(self):
        result = {}
        for d in self.data:
            result[d['name']] = d['value'] #* {field_name: User input data}
        return result

    def get_data(self):
        result = []
        for data in self.data:
            data_ = data
            if data['genre'] == const.FieldGenre.UPLOAD_FILE.value and data['value'] is not None:
                data_['value'] = data['value']['url_path']
                result.append(data_)
            else:
                result.append(data_)
        return result



def save_form_response(form: Form, form_data: dict, user_ip: str):
    #* You can access `request` from form_data
    form.save_response(form_data, user_ip)