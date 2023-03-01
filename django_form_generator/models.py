import uuid
from datetime import datetime
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.core.cache import cache

from django_form_generator.common.models import BaseModel
from django_form_generator.common.helpers import FileFieldHelper
from django_form_generator.common.utils import (
    APICall,
    evaluate_data,
    get_client_ip
)

from django_form_generator import const
from django_form_generator.settings import form_generator_settings as fg_settings


CONTENT_TYPE_MODELS_LIMIT = models.Q(
    app_label="django_form_generator", model="field"
) | models.Q(app_label="django_form_generator", model="option")


class FieldCategory(BaseModel):
    title = models.CharField(_("Title"), max_length=200, unique=True)
    is_active = models.BooleanField(_("Is Active"), default=True)
    parent = models.ForeignKey(
        "self",
        verbose_name=_("Parent Category"),
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        limit_choices_to={"is_active": True},
        related_name="children",
    )
    weight = models.PositiveIntegerField(_("Weight"))

    class Meta:
        verbose_name = _("FieldCategory")
        verbose_name_plural = _("FieldCategories")
        ordering = ("weight",)
        indexes = [
            models.Index(fields=("title",), name="f_g_%(class)s_title"),
            models.Index(fields=("is_active",), name="f_g_%(class)s_active"),
            models.Index(fields=("weight",), name="f_g_%(class)s_weight"),
        ]

    def __str__(self) -> str:
        return self.title

    def get_fields(self):
        return self.fields.filter(is_active=True)  # type: ignore


class Form(BaseModel):
    title = models.CharField(_("Title"), max_length=200)
    slug = models.SlugField(_("Slug"), unique=True, allow_unicode=True)
    status = models.CharField(
        _("Status"),
        max_length=50,
        choices=const.FormStatus.choices,
        default=const.FormStatus.DRAFT,
    )
    submit_text = models.CharField(
        _("Submit Text"), max_length=100, default=_("Submit")
    )
    redirect_url = models.URLField(
        _("Redirect URL"), max_length=200, blank=True, null=True
    )
    success_message = models.CharField(
        _("Success Message"), max_length=255, blank=True, null=True
    )
    style = models.CharField(
        _("Style"),
        max_length=300,
        blank=True,
        null=True,
        help_text=_(
            "Inline: 2 field in every row."
            "Inorder: 1 field in every row."
            "dynamic: can dynamicly style the field in FormFieldThrough section/table."
        ),
    )
    direction = models.CharField(
        _("Direction"),
        max_length=3,
        choices=const.FormDirection.choices,
        default=const.FormDirection.LTR,
    )
    limit_to = models.PositiveIntegerField(
        _("Limit Submiting Form"), blank=True, null=True
    )
    valid_from = models.DateTimeField(_("Valid From"), blank=True, null=True)
    valid_to = models.DateTimeField(_("Valid To"), blank=True, null=True)
    fields = models.ManyToManyField(
        "django_form_generator.Field",
        verbose_name=_("Fields"),
        through="django_form_generator.FormFieldThrough",
        related_name="forms",
    )
    apis = models.ManyToManyField(
        "django_form_generator.FormAPIManager",
        verbose_name=_("Apis"),
        through="django_form_generator.FormAPIThrough",
        related_name="forms",
    )
    is_editable = models.BooleanField(_("Is Editable"), default=False)

    objects = fg_settings.FORM_MANAGER()  # type: ignore

    class Meta:
        verbose_name = _("Form")
        verbose_name_plural = _("Forms")

        indexes = [
            models.Index(fields=("title",), name="f_g_%(class)s_title"),
            models.Index(fields=("slug",), name="f_g_%(class)s_slug"),
            models.Index(fields=("status",), name="f_g_%(class)s_status"),
        ]

    def __str__(self) -> str:
        return self.title

    def get_absolute_url(self):
        return reverse("django_form_generator:form_detail", kwargs={"pk": self.pk})

    def __call_and_set_cache(self, api, cache_key, response_data, set_cache):
        response = APICall(
            api.method.lower(),
            api.url,
            api.body,
            response_data,
            headers=api.headers,
        )
        status_code, result, body = response.get_result()
        if set_cache:
            cache.set(cache_key, (api, status_code, result, body))
        return api, status_code, result, body

    def __call_apis(
        self, execute_time: const.FormAPIManagerExecuteTime, response_data: dict
    ):
        request = response_data['request']
        cache_key = "FormAPIs_{}_{}_{}"

        responses = []
        for api in self.apis.filter(is_active=True, execute_time=execute_time).order_by('form_apis__weight'):
            api: FormAPIManager
            if api.cache_by:
                if api.cache_by == const.CacheMethod.SESSION_KEY:
                    cache_method = request.session.session_key
                elif api.cache_by == const.CacheMethod.USER_ID and request.user.is_authenticated:
                    cache_method = request.user.id
                else:
                    cache_method = get_client_ip(request)
                cache_key = cache_key.format(self.pk, execute_time, cache_method)
                cached_response = cache.get(cache_key)
                if cached_response:
                    responses.append(cached_response)
                else:
                    response = self.__call_and_set_cache(api, cache_key, response_data, True)
                    responses.append(response)

            else:
                response = self.__call_and_set_cache(api, cache_key, response_data, False)
                responses.append(response)

        return responses

    def call_post_apis(self, response_data: dict):
        return self.__call_apis(
            const.FormAPIManagerExecuteTime.POST_LOAD, response_data
        )

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

    def get_fields(self, extra: dict | None = None):
        conds = {"is_active": True}
        if extra:
            conds.update(extra)
        return self.fields.filter(**conds).order_by(
            models.F("form_field_through__category__weight").asc(
                nulls_last=True),
            "form_field_through__weight",
        )
    
    @property
    def render_fields(self):
        data = []
        for field in self.get_fields():
            field: "Field"
            form_field_through = self.form_field_through.filter(field_id=field.id).last()  # type: ignore
            attrs = field.build_serializer_attrs()
            attrs.update(
                {
                    "parent_object_id": field.object_id,
                    "parent_content_type": getattr(field.content_type, "model", None),
                    "placeholder": field.placeholder,
                    "position": form_field_through.position,
                    "options": field.get_choices().values('id', 'name'),
                    "validators": [{'code': validator.code, 'limit_value': validator.limit_value, 'message': validator.message} for validator in attrs.get('validators',[])]
                })
            data.append({
                    "id": field.id,
                    "name": field.name,
                    "type": field.genre,
                    "category": getattr(form_field_through.category, 'title', None),
                    "attrs": attrs
                })

        return data


class FormFieldThrough(models.Model):
    form = models.ForeignKey(
        "django_form_generator.Form",
        verbose_name=_("Form"),
        on_delete=models.CASCADE,
        related_name="form_field_through",
    )
    field = models.ForeignKey(
        "django_form_generator.Field",
        verbose_name=_("Field"),
        on_delete=models.CASCADE,
        related_name="form_field_through",
    )
    position = models.CharField(
        _("Position"),
        max_length=100,
        choices=const.FieldPosition.choices,
        default=const.FieldPosition.BREAK,
    )
    category = models.ForeignKey(
        "django_form_generator.FieldCategory",
        verbose_name=_("Category"),
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        limit_choices_to={"is_active": True},
        related_name="form_field_through",
    )
    weight = models.PositiveIntegerField(_("Weight"))

    class Meta:
        ordering = ("weight",)
        indexes = [
            models.Index(fields=("weight",), name="f_g_%(class)s_weight"),
        ]
        constraints = [
            models.UniqueConstraint(fields=['field', 'form'],
                name='form_field_unique',
            ),
        ]

    def __str__(self) -> str:
        return f"{self.form.title} | {self.field.name}"


class Field(BaseModel):
    label = models.CharField(_("Label"), max_length=100)
    name = models.CharField(_("Name"), max_length=100, blank=True, unique=True)
    genre = models.CharField(
        _("Genre"), max_length=80, choices=const.FieldGenre.choices
    )
    is_required = models.BooleanField(_("Is Required"), default=True)
    placeholder = models.CharField(
        _("Placeholder"), max_length=100, blank=True, null=True
    )
    default = models.CharField(
        _("Default Value"), max_length=255, blank=True, null=True
    )
    help_text = models.CharField(
        _("Help Text"), max_length=200, blank=True, null=True)
    write_only = models.BooleanField(_("Write Only"), default=False)
    read_only = models.BooleanField(_("Read Only"), default=False)
    options = models.ManyToManyField(
        "django_form_generator.Option",
        through="django_form_generator.FieldOptionThrough",
        verbose_name=_("Options"),
        related_name="fields",
        help_text=_(
            "Only for multi value fields like Dropdown, Radio, Checkbox, etc..."
        ),
    )
    is_active = models.BooleanField(_("Is Active"))
    # depends
    content_type = models.ForeignKey(
        "contenttypes.ContentType",
        verbose_name=_("Depends On Object"),
        on_delete=models.SET_NULL,
        related_name="fields",
        limit_choices_to=CONTENT_TYPE_MODELS_LIMIT,
        blank=True,
        null=True,
    )
    object_id = models.BigIntegerField(
        _("Depends on Object ID"), blank=True, null=True)
    content_object = GenericForeignKey()

    depends = GenericRelation('self')

    class Meta:
        verbose_name = _("Field")
        verbose_name_plural = _("Fields")
        indexes = [
            models.Index(fields=("label",), name="f_g_%(class)s_label"),
            models.Index(fields=("name",), name="f_g_%(class)s_name"),
            models.Index(fields=("genre",), name="f_g_%(class)s_genre"),
        ]

    def __str__(self) -> str:
        return self.label

    def build_serializer_attrs(self, extra_attrs: dict | None = None):
        attrs = {
            "allow_null": not self.is_required,
            "help_text": self.help_text,
            "label": self.label,
            "read_only": self.read_only,
            "write_only": self.write_only,
            }
        validators = self.validators.filter(is_active=True)
        if validators.exists():
            attrs.update(
                {
                    "validators": [
                        val.generate_validator() for val in validators
                    ]
                }
            )
        if self.default:
            attrs.update({'initial': self.default})
        if extra_attrs:
            attrs.update(extra_attrs)
        return attrs

    def build_field_attrs(self, extra_attrs: dict | None = None):
        attrs = {
            "required": self.is_required,
            "help_text": self.help_text,
            "label": self.label,
        }

        validators = self.validators.filter(is_active=True)
        if validators.exists():
            attrs.update(
                {
                    "validators": [
                        val.generate_validator() for val in validators
                    ]
                }
            )
        if self.default is not None:
            attrs.update({"initial": self.default})

        if extra_attrs:
            attrs.update(extra_attrs)
        return attrs

    def build_widget_attrs(self, form, extra_attrs: dict | None = None):
        form_field_through = self.form_field_through.filter(form_id=form.id).last()  # type: ignore
        attrs = {"instance_id": self.pk,
                 "position": form_field_through.position,
                 "readonly": self.read_only,}

        if self.genre in const.FieldGenre.selectable_fields():
            attrs.update({"onchange": "onElementChange(this)"})
        else:
            attrs.update({"onkeypress": "onElementChange(this)"})

        if self.content_object is not None:
            attrs.update(
                {
                    "parent_object_id": self.object_id,
                    "parent_content_type": self.content_type.model,
                    "disabled": True
                }
            )

        if form_field_through.category is not None:
            attrs.update({"category": form_field_through.category.title})

        if self.placeholder is not None:
            attrs.update({"placeholder": self.placeholder})

        if extra_attrs:
            attrs.update(extra_attrs)
        return attrs

    def get_choices(self):
        return self.options.filter(is_active=True).order_by("field_options__weight")


class FieldValidator(BaseModel):
    field = models.ForeignKey("django_form_generator.Field", verbose_name=_("Field"), on_delete=models.PROTECT, related_name='validators')
    validator = models.CharField(_("Validator"), choices=const.Validator.choices, max_length=100)
    value = models.CharField(_("Value"), max_length=255)
    error_message = models.CharField(_("Error Message"), max_length=500, blank=True, null=True)
    is_active = models.BooleanField(_("Is Active"), default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['field', 'validator'],
                name='field_validator_unique',
            ),
        ]
    
    def __str__(self):
        return ' | '.join((self.field.name, self.validator, self.value))

    def generate_validator(self):
        return const.Validator(self.validator).validate(self.value, self.error_message)


class FieldOptionThrough(models.Model):
    field = models.ForeignKey(
        "django_form_generator.Field",
        verbose_name=_("Field"),
        on_delete=models.CASCADE,
        related_name="field_options",
    )
    option = models.ForeignKey(
        "django_form_generator.Option",
        verbose_name=_("Option"),
        on_delete=models.CASCADE,
        related_name="field_options",
    )
    weight = models.PositiveIntegerField(_("Weight"))

    class Meta:
        ordering = ("weight",)
        indexes = [models.Index(
            fields=("weight",), name="f_g_%(class)s_weight")]

    def __str__(self) -> str:
        return f"{self.field.name} | {self.option.name}"


class Option(BaseModel):
    name = models.CharField(_("Name"), max_length=100)
    is_active = models.BooleanField(_("Is Active"), default=True)

    class Meta:
        verbose_name = _("Option")
        verbose_name_plural = _("Options")
        indexes = [
            models.Index(fields=("name",), name="f_g_%(class)s_name"),
        ]

    def __str__(self) -> str:
        return self.name


class FormAPIThrough(models.Model):
    form = models.ForeignKey(
        "django_form_generator.Form",
        verbose_name=_("Form"),
        on_delete=models.CASCADE,
        related_name="form_apis",
    )
    api = models.ForeignKey(
        "django_form_generator.FormAPIManager",
        verbose_name=_("API"),
        on_delete=models.CASCADE,
        related_name="form_apis",
    )
    weight = models.PositiveIntegerField(_("Weight"))

    class Meta:
        ordering = ("weight",)
        indexes = [models.Index(
            fields=("weight",), name="f_g_%(class)s_weight")]

    def __str__(self) -> str:
        return f"{self.form.title} | {self.api.title}"


class FormAPIManager(BaseModel):
    title = models.CharField(_("Title"), max_length=200)
    url = models.URLField(_("URL"), max_length=200)
    headers = models.JSONField(_("Headers"), blank=True, null=True)
    method = models.CharField(
        _("Method"), max_length=50, choices=const.FormAPIManagerMethod.choices
    )
    body = models.TextField(_("Body"), blank=True, null=True)
    execute_time = models.CharField(
        _("Execute Time"),
        max_length=50,
        choices=const.FormAPIManagerExecuteTime.choices,
    )
    response = models.TextField(_("Response"), blank=True, null=True)
    cache_by = models.CharField(_("Cache By"), max_length=15, choices=const.CacheMethod.choices, blank=True, null=True)
    is_active = models.BooleanField(_("Is Active"))

    class Meta:
        verbose_name = _("FormAPIManager")
        verbose_name_plural = _("FormAPIManagers")
        indexes = [
            models.Index(fields=("title",), name="f_g_%(class)s_title"),
            models.Index(fields=("method",), name="f_g_%(class)s_method"),
            models.Index(fields=("is_active",), name="f_g_%(class)s_active"),
        ]

    def __str__(self) -> str:
        return self.title


class FormResponseBase(BaseModel):
    unique_id = models.UUIDField(
        _("Unique ID"), unique=True, default=uuid.uuid4)
    form = models.ForeignKey(
        "django_form_generator.Form",
        verbose_name=_("Form"),
        on_delete=models.PROTECT,
        related_name="%(class)s_responses",
    )
    data = models.JSONField(_("Data"))
    api_response = models.JSONField(_("Api Respons"), blank=True, null=True)

    class Meta:
        abstract = True

    def _str_(self):
        return self.form.title

    def save(self, *args, **kwargs):
        if self.unique_id is None:
            self.unique_id = uuid.uuid4()
        return super().save(*args, **kwargs)

    @property
    def pure_data(self):
        result = {}
        for d in self.data:
            result[d["name"]] = d["value"]  # * {field_name: User input data}
        return result

    def get_data(self):
        result = []
        for data in self.data:
            data_ = data.copy()
            if (
                data["genre"] == const.FieldGenre.UPLOAD_FILE.value
                and data["value"] is not None
            ):
                data_["value"] = FileFieldHelper(
                    data["value"]["url"], data["value"]["directory"]
                )
                result.append(data_)
            elif data_["value"] and data_["value"] !='None' and data["genre"] in (const.FieldGenre.DATETIME, const.FieldGenre.DATE):
                data_["value"] = datetime.fromisoformat(data_["value"])
                result.append(data_)
            else:
                result.append(data_)
        return result

    @classmethod
    def _generate_api_result(cls, results):
        data = []
        for api, status_code, result, body in results:
            data.append(
                {
                    "api": api.id,
                    "url": api.url,
                    "method": api.method,
                    "body": body or api.body,
                    "response_status_code": status_code,
                    "result": result,
                }
            )
        return data or None

    @classmethod
    def _generate_data(cls, form, form_data, instance=None):
        data = []
        request = form_data["request"]
        for field in form.get_fields():
            field_value = form_data.get(field.name, None)
            kwargs = {}
            if field.genre == const.FieldGenre.UPLOAD_FILE:
                pure_data = instance.pure_data.get(field.name) if instance else None
                kwargs.update({'host':  request._current_scheme_host,
                            'instance_directory': pure_data.get("directory") if pure_data else None })
            field_value = const.FieldGenre(field.genre).evaluate(field_value, **kwargs)

            category_title = field.form_field_through.filter(form_id=form.pk). \
                values_list('category__title', flat=True).last()

            new_data = {
                "id": field.id,
                "name": field.name,
                "label": field.label,
                "genre": field.genre,
                "category": category_title,
                "value": field_value,
                "depends_on": None
            }
            if field.content_object:
                new_data["depends_on"] = {"id": field.object_id, 
                                            "type": field.content_type.model}
            data.append(
                new_data
            )
        return data or None


class FormResponse(FormResponseBase):
    user_ip = models.GenericIPAddressField(
        _("IP Address"), blank=True, null=True)

    class Meta:
        verbose_name = _("Form Response")
        verbose_name_plural = _("Form Responses")
        indexes = [
            models.Index(fields=("user_ip",), name="f_g_%(class)s_user"),
            models.Index(fields=("unique_id",),
                         name="f_g_%(class)s_unique_id"),
        ]

    @classmethod
    def save_response(cls, form, data, user_ip=None, update_form_response_id=None):
        api_response = []
        pre_result = form.call_pre_apis(data)
        post_result = form.call_post_apis(data)
        pre = cls._generate_api_result(pre_result)
        post = cls._generate_api_result(post_result)
        if pre:
            api_response.append(pre)
        if post:
            api_response.append(post)
        if update_form_response_id is None:
            response = FormResponse.objects.create(
                data=cls._generate_data(form, data),
                user_ip=user_ip,
                api_response=api_response or None,
                form=form,
            )
        else:
            response = FormResponse.objects.get(id=update_form_response_id)
            response.data = cls._generate_data(form, data, response)
            response.api_response = api_response or response.api_response
            response.save()
        return response


def save_form_response(
    form: Form,
    form_data: dict,
    user_ip: str | None = None,
    update_form_response_id: int | None = None,
):
    # * You can access `request` from form_data
    FormResponse.save_response(
        form, form_data, user_ip, update_form_response_id)
