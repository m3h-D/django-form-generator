from django.db.models import TextChoices
from django.utils.translation import gettext_lazy as _
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
        return [cls.DROPDOWN, cls.CHECKBOX, cls.RADIO, cls.MULTI_CHECKBOX]

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
    FILE_SIZE = 'file-size', _('File size')

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

    def validate(self, value, error_message=None):
        return self.__validators_map()[self](value, error_message)


class CacheMethod(TextChoices):
    SESSION_KEY = 'session_key', _('Session Key')
    USER_ID = 'user_id', _('User ID')
    USER_IP = 'user_ip', _('User IP')