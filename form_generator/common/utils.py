import requests
import uuid
import os
from django.conf import settings
from django.template import Template, Context
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _
from django.core.validators import BaseValidator

from form_generator.const import FormAPIManagerMethod
from form_generator.settings import form_generator_settings


def upload_file_handler(f):
    new_filename = uuid.uuid4()
    _, ext = os.path.splitext(f.name)
    directory = f'form_generator/{new_filename}{ext}'
    dest = os.path.join(settings.MEDIA_ROOT, directory)
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
        if form_generator_settings.FORM_EVALUATIONS['form_data'] in data:
            replace_with['form_data'] = mark_safe(replace_with)
        template = Template(data)
        context = Context(replace_with)
        data = template.render(context)
        return data
    else:
        return replace_with


class APICall:

    def __init__(self, method, url, body: str|None=None, data_response: dict|list|None=None, **kwargs):
        request = getattr(requests, method)
        if data_response is not None:
            url = evaluate_data(url, data_response)
        if method == FormAPIManagerMethod.GET:
            response = request(url, **kwargs)
        else:
            if data_response is not None:
                body = evaluate_data(body, data_response) #type: ignore
            response = request(url, data=body, **kwargs)
        result = response.json()
        self.status_code: int = response.status_code
        self.result: dict = result

    def get_result(self) -> tuple[int, dict]:
        return  self.status_code, self.result


class FileSizeValidator(BaseValidator):

    def compare(self, file_, limit_value):
        return file_.size > limit_value