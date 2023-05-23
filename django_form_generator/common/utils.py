import requests
import uuid
import os
import ast
from pathlib import Path
from typing import Any
from django.conf import settings
from django.template import Template, Context
from django.utils.safestring import mark_safe
from django.contrib import messages
from django.utils.translation import gettext as _
from django.core.validators import BaseValidator
from django.utils.module_loading import import_string
from django.db import models

from django_form_generator.const import FormAPIManagerMethod, FieldLookupType, FieldGenre
from django_form_generator.settings import form_generator_settings as fg_settings


FILE_UPLOAD_DIRECTORY = os.path.join(settings.MEDIA_ROOT, 'django_form_generator')

try:
    Path(FILE_UPLOAD_DIRECTORY).mkdir(exist_ok=True)
except Exception as e:
    print(e)

def upload_file_handler(f):
    new_filename = uuid.uuid4()
    _, ext = os.path.splitext(f.name)
    dest = FILE_UPLOAD_DIRECTORY + f'/{new_filename}{ext}'
    with open(dest, 'wb+') as destination:
        for chunk in f.chunks():
            destination.write(chunk)
    return dest


def get_client_ip(request):
    """get the client IP address"""
    remote_address = request.META.get('REMOTE_ADDR')
    ip = remote_address
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        proxies = x_forwarded_for.split(',')
        while (len(proxies) > 0):
            proxies.pop(0)
        if len(proxies) > 0:
            ip = proxies[0]
    return ip


def evaluate_data(data: str, replace_with: dict|list) -> str | list:
    """replace data that wrapped in a pattern like: {{sample}} with provided dictionary

    Args:
        data (str): 'hello {{first_name}} {{last_name}}'
        replace_with (dict): {'first_name': 'john', 'last_name', 'doe'}

    Returns:
        str: 'hello john doe'
    """
    if isinstance(replace_with, list):
        l_data = []
        for item in replace_with:
            l_data.append(evaluate_data(data, item))
        return l_data
    elif isinstance(replace_with, dict):
        if fg_settings.FORM_EVALUATIONS['form_data'] in data:
            replace_with['form_data'] = mark_safe(replace_with)
        template = Template(data)
        context = Context(replace_with)
        data = template.render(context)
        return data
    else:
        return replace_with


class APICall:
    body = None
    status_code = None
    result = None

    def __init__(self, method, url, body: str|None=None, data_response: dict|list|None=None, **kwargs):
        request = getattr(requests, method)
        if data_response is not None:
            url = evaluate_data(url, data_response)
        if method == FormAPIManagerMethod.GET:
            response = request(url, **kwargs)
        else:
            if data_response is not None:
                self.body = body = evaluate_data(body, data_response) #type: ignore
            response = request(url, data=body, **kwargs)
        try:
            result = response.json()
            self.result: dict = result
        except Exception as e:
            self.result: dict = {"error": response.reason}
        self.status_code: int = response.status_code

    def get_result(self) -> tuple[int, dict, dict]:
        return  self.status_code, self.result, self.body


class FileSizeValidator(BaseValidator):

    def compare(self, file_, limit_value):
        return file_.size > limit_value


class FilterMixin:

    field_path: str = 'data'
    _filters: set = set()
    
    def clean_parameters(self, item):
        return list(filter(lambda x: x != '', item))

    def _evaluate_value(self, value, genre):
        try:
            value = ast.literal_eval(value)
        except (ValueError, SyntaxError):
            value = str(value)
        if isinstance(value, (list, tuple)):
            temp_val = []
            for v in value:
                temp_val.append(FieldGenre(genre).evaluate(v, regex=True))
        else:
            temp_val = FieldGenre(genre).evaluate(value, regex=True)
        return temp_val

    def _evaluate_filter(self, field_id:int, index: int, value: Any, field_lookup: str) -> models.Q:
        if field_lookup.startswith('not'):
            field_lookup = field_lookup.lstrip('not_')
            negate = True
        else:
            negate = False
        lookup = '__' + FieldLookupType(field_lookup).value
        if field_lookup == 'range':
            inner_lookup = models.Q(**{f"{self.field_path}__{index}__value__gte": value[0], 
                                       f"{self.field_path}__{index}__value__lte": value[1]})
        else:
            inner_lookup = models.Q(**{f"{self.field_path}__{index}__value{lookup}": value})
        inner_lookup &= models.Q(**{f"{self.field_path}__{index}__id": field_id})
        if negate:
            i_lookup = ~inner_lookup
            inner_lookup = i_lookup
        
        return inner_lookup

    def _evaluate_related_field(self, response: "FormResponse", form: "Form", field_id: int, field_ids: list[str], values:list[str], index:int, field_lookup: str):
        fields = form.get_fields(extra={"object_id": field_id, "content_type__model": 'field', "id__in": field_ids})
        for field in fields.iterator():
            value =  self._evaluate_value(values[index], field.genre)
            new_filters = self._evaluate_filter(field.pk, index, value, field_lookup)
            if str(new_filters) not in self._filters:
                query = response.filter(new_filters)
                self._filters.add(str(new_filters))
                return models.Exists(query)


    def get_lookups(self, request) -> tuple[models.Q, dict]:
        form_id ,field_ids ,field_lookups ,operands ,values = self.get_parameters(request)
        if form_id:
            form_id = int(form_id)
            Form = import_string('django_form_generator.models.Form')
            FormResponse = import_string('django_form_generator.models.FormResponse')

            form = Form.objects.prefetch_related('fields').get(id=form_id)
            response = FormResponse.objects.filter(form_id=form_id)
            if response.exists():
                self._filters: set = set()
                response_annotations: dict = {}
                response_filters: models.Q = models.Q()
                for i, value in enumerate(values):
                    try:
                        field_id = int(field_ids[i])
                        field_lookup = field_lookups[i]
                        operand = operands[i]
                    except IndexError:
                        messages.add_message(request, messages.ERROR, _("Please make sure you filled all the fields [Operand, Field, Field lookup, Value] for Data filter."))
                        return models.Q(), {}
                    form_fields_list = form.get_fields()
                    current_field = form_fields_list.only('id', 'name').get(id=field_id)
                    value = self._evaluate_value(value, current_field.genre)
                    related_index = next((field_ids.index(str(f.id)) 
                                        for f in current_field.depends.values_list('id', flat=True) 
                                        if str(f.id) in field_ids), None)
                    index = list(form_fields_list.values_list('id', flat=True)).index(field_id)
                    new_filters = self._evaluate_filter(field_id, index, value, field_lookup)
                    new_filters_ = models.Q()
                    if related_index:
                        # generate related field lookup & annotation and add it to current field lookup
                        related_exists = self._evaluate_related_field(response, form, field_id, field_ids, values, related_index, field_lookups[related_index])
                        if related_exists:
                            response_annotations.update({f'{field_id}_{i}_related_exists': related_exists})
                            related_lookup = models.Q(**{f'{field_id}_{i}_related_exists': True})

                            new_filters.add(related_lookup, models.Q.AND)
                            new_filters_.add(related_lookup, models.Q.AND)
                    if str(new_filters) not in self._filters: # check if this filter is not duplicate
                        self._filters.add(str(new_filters))
                        exists = models.Exists(response.filter(new_filters, id=models.OuterRef('id')))
                        response_annotations.update({f'{field_id}_{i}_exists':exists})
                        new_filters_.add(models.Q(**{f'{field_id}_{i}_exists': True}), operand)
                        response_filters.add(new_filters_, operand)

                response_filters.add(models.Q(form_id=form_id), models.Q.AND)
                return response_filters, response_annotations
        if len(values) > 0:
            messages.add_message(request, messages.ERROR, _("Please make sure you have entered form id for Data filter."))
        return models.Q(), {}

    def queryset(self, request, queryset):
        response_filters, response_annotations = self.get_lookups(request)
        return queryset.alias(**response_annotations).filter(response_filters)
