from django import template
from django.urls import reverse
from django.http import QueryDict
from django.utils.safestring import mark_safe
from django.core.cache import cache

from core.models import Form, FormDetail
from core.views import FormGeneratorView




register = template.Library()

@register.inclusion_tag('form_generator/form_tag.html')
def render_form(form_id: int):
    return {'url': reverse('form_generator:form_detail', args=(form_id,))}


@register.filter(name='add_attribute')
def add_attribute(item, attr):
    for attr_key, attr_value in QueryDict(attr).items():
        item.field.widget.attrs[attr_key] = item.field.widget.attrs.get(attr_key, '') + ' ' + attr_value
    return item

@register.simple_tag()
def render_pre_api(form_id, api_id=None):
    try:
        form_detail = FormDetail.objects.filter_valid().get(form_id=form_id)
    except FormDetail.DoesNotExist:
        return 'Form id is not valid'
    else:
        responses = form_detail.form.render_pre_apis()
        if api_id:
            responses = mark_safe(next((result for api_id_, result in responses if api_id_ == api_id)))
        else:
            responses = mark_safe('<br>'.join([result for _, result in responses]))
        return responses


@register.simple_tag()
def render_post_api(form_id, api_id=None):
    try:
        form_detail = FormDetail.objects.filter_valid().get(form_id=form_id)
    except FormDetail.DoesNotExist:
        return 'Form id is not valid'
    else:
        responses = form_detail.form.render_post_apis()
        if api_id:
            responses = mark_safe(next((result for api_id_, result in responses if api_id_ == api_id)))
        else:
            responses = mark_safe('<br>'.join([result for _, result in responses]))
        return responses