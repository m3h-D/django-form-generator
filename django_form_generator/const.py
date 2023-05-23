from django.db.models import TextChoices
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.core.validators import (MaxValueValidator, 
                                    MinValueValidator, 
                                    MaxLengthValidator, 
                                    MinLengthValidator, 
                                    RegexValidator,
                                    FileExtensionValidator,
                                    )
from django.utils.module_loading import import_string


class FormStatus(TextChoices):
    DRAFT = 'draft', _('Draft')
    PENDING = 'pending', _('Pending')
    PUBLISH = 'publish', _('Publish')
    SUSPEND = 'suspend', _('Suspend')

class FieldGenre(TextChoices):
    TEXT_INPUT = 'text_input', _('Text input')
    MULTI_TEXT_INPUT = 'multi_text_input', _('Multi-Text input')
    TEXT_AREA = 'text_area', _('Text area')
    NUMBER = 'number', _('Number')
    DROPDOWN = 'dropdown', _('Dropdown')
    DATE = 'date', _('Date')
    TIME = 'time', _('Time')
    DATETIME = 'datetime', _('Datetime')
    EMAIL = 'email', _('E-Mail')
    PASSWORD = 'password', _('Password')
    CHECKBOX = 'checkbox', _('Checkbox')
    MULTI_CHECKBOX = 'multi_checkbox', _('Multi checkbox')
    RADIO = 'radio', _('Radio')
    HIDDEN = 'hidden', _('Hidden')
    CAPTCHA = 'captcha', _('Captcha')
    UPLOAD_FILE = 'upload_file', _('Upload file')

    @classmethod
    def selectable_fields(cls):
        return [cls.DROPDOWN, cls.RADIO, cls.MULTI_CHECKBOX]

    def evaluate(self, value, **kwargs):
        return getattr(self, "eval_" + self.name.lower())(value, **kwargs)

    def eval_text_input(self, value, **kwargs):
        if value is None or value == '':
            return None
        return str(value)

    def eval_multi_text_input(self, value, **kwargs):
        if value is None or value == '':
            return []
        if isinstance(value, list):
            return [str(val) for val in value]
        else:
            return []

    def eval_text_area(self, value, **kwargs):
        if value is None or value == '':
            return value
        return self.eval_text_input(value)

    def eval_number(self, value, **kwargs):
        if value is None or value == '':
            return None
        return int(value)

    def eval_dropdown(self, value, **kwargs):
        if kwargs.get('regex'):
            return self.eval_text_input(value)
        return self.eval_number(value)

    def eval_date(self, value, **kwargs):
        return self.eval_text_input(value)

    def eval_time(self, value, **kwargs):
        return self.eval_text_input(value)

    def eval_datetime(self, value, **kwargs):
        return self.eval_text_input(value)

    def eval_email(self, value, **kwargs):
        return self.eval_text_input(value)

    def eval_password(self, value, **kwargs):
        return self.eval_text_input(value)

    def eval_checkbox(self, value, **kwargs):
        return bool(value)

    def eval_multi_checkbox(self, value, **kwargs):
        if value is None or value == '':
            return []
        if isinstance(value, list):
            return [int(val) for val in value]
        else:
            return []

    def eval_radio(self, value, **kwargs):
        if kwargs.get('regex'):
            return self.eval_text_input(value)
        return self.eval_number(value)

    def eval_hidden(self, value, **kwargs):
        return self.eval_text_input(value)

    def eval_captcha(self, value, **kwargs):
        return None

    def eval_upload_file(self, value, **kwargs):
        FileFieldHelper = import_string('django_form_generator.common.helpers.FileFieldHelper')

        if (
            value is not None
            and not isinstance(value, dict)
        ):
            return FileFieldHelper.upload_file(
                kwargs['host'], value, kwargs['instance_directory']
            )
        return  value


class FormAPIManagerMethod(TextChoices):
    GET = 'get', _('GET')
    POST = 'post', _('POST')
    PUT = 'put', _('PUT')
    PATCH = 'patch', _('PATCH')
    DELETE = 'delete', _('DELETE')
    OPTION = 'option', _('OPTION')

class FormAPIManagerExecuteTime(TextChoices):
    PRE_LOAD = 'pre_load', _('Pre load')
    POST_LOAD = 'post_load', _('Post load')

class FieldPosition(TextChoices):
    INLINE = 'inline', _('In-line')
    INORDER = 'inorder', _('In-Order')
    BREAK = 'break', _('Break')

class FormDirection(TextChoices):
    LTR = 'ltr', _('LTR')
    RTL = 'rtl', _('RTL')

class FormStyle(TextChoices):
    INLINE = 'django_form_generator/fields/inline_fields.html', _('In-line')
    INORDER = 'django_form_generator/fields/inorder_fields.html', _('In-order')
    DYNAMIC = 'django_form_generator/fields/dynamic_fields.html', _('Dynamic')


class Validator(TextChoices):
    MAX_LENGTH = 'max-length', _('Max length')
    MIN_LENGTH = 'min-length', _('Min length')
    MAX_VALUE = 'max-value', _('Max value')
    MIN_VALUE = 'min-value', _('Min value')
    REGEX = 'regex', _('Regex')
    FILE_EXTENTION = 'file-extention', _('File extention')
    FILE_SIZE = 'file-size', _('File size (MB)')

    @classmethod
    def __validators_map(cls):
        FileSizeValidator = import_string('django_form_generator.common.utils.FileSizeValidator')

        validators_map = {
        cls.MAX_LENGTH: MaxLengthValidator,
        cls.MIN_LENGTH: MinLengthValidator,
        cls.MAX_VALUE: MaxValueValidator,
        cls.MIN_VALUE: MinValueValidator,
        cls.REGEX: RegexValidator,
        cls.FILE_EXTENTION: FileExtensionValidator,
        cls.FILE_SIZE: FileSizeValidator,
        }
        return validators_map

    def clean(self, value):
        getattr(self, "clean_" + self.name.lower())(value)

    def evaluate(self, value):
        return getattr(self, "eval_" + self.name.lower())(value)

    def eval_max_length(self, value):
        return int(value)

    def eval_min_length(self, value):
        return int(value)

    def eval_max_value(self, value):
        return int(value)

    def eval_min_value(self, value):
        return int(value)

    def eval_file_extention(self, value):
        return value.split(',')

    def eval_file_size(self, value):
        return float(value) * 2 ** 20

    def clean_max_length(self, value):
        try:
            int(value)
        except ValueError:
            raise ValidationError(_("Value for %s should be integer") % self.label)

    def clean_min_length(self, value):
        self.clean_max_length(value)

    def clean_max_value(self, value):
        self.clean_max_length(value)

    def clean_min_value(self, value):
        self.clean_max_length(value)

    def clean_file_extention(self, value):
        if ',' not in value and len(value.split(' ')) > 1:
            raise ValidationError(_('Separate values with comma for %s like: jpg,png,...') % self.label)

    def clean_file_size(self, value):
        try:
            float(value)
        except ValueError:
            raise ValidationError(_("Value for %s should be integer or float") % self.label)

    def validate(self, value, error_message=None):
        value = self.evaluate(value)
        return self.__validators_map()[self](value, error_message)


class CacheMethod(TextChoices):
    SESSION_KEY = 'session_key', _('Session Key')
    USER_ID = 'user_id', _('User ID')
    USER_IP = 'user_ip', _('User IP')

class FieldLookupType(TextChoices):
    ICONTAINS = 'icontains', _('Contains')
    IEXACT = 'iexact', _('Exact')
    ISNULL = 'isnull', _('Is null')
    IREGEX = 'iregex', _('Regex')
    RANGE = 'range', _('Range')
    IN = 'in', _('In')
    NOT_ICONTAINS = 'not_icontains', _('Not contains')
    NOT_IEXACT = 'not_iexact', _('Not exact')
    NOT_IREGEX = 'not_iregex', _('Not regex')
    NOT_RANGE = 'not_range', _('Not range')
    NOT_IN = 'not_in', _('Not in')
