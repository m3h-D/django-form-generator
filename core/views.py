from django.shortcuts import render
from django.views.generic import DetailView, FormView, CreateView
from django.views.generic.edit import FormMixin
from django.contrib import messages
from django.utils.translation import gettext as _
from django.http import HttpResponseRedirect

from django_htmx.http import HttpResponseClientRedirect
# Create your views here.

from common.utils import get_client_ip
from core.models import Form, FormResponse, FormDetail
from core.forms import FormGeneratorForm


def home_page(request):
    return render(request, 'base.html', {})


class FormGeneratorView(FormMixin, DetailView):
    context_object_name = "form_generator"
    queryset = FormDetail.objects.filter_valid()
    model = FormDetail
    slug_field =  "form__id"
    slug_url_kwarg =  "form_id"
    template_name = "form_generator/form.html"
    form_class = FormGeneratorForm

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        self.object.form.render_pre_apis()
        return response

    def get_success_url(self) -> str:
        return self.object.redirect_url or self.request.META.get("HTTP_REFERER") # type: ignore

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"user_ip": get_client_ip(self.request), 
                        "form_detail": self.object, 
                        "ignore_disabled": self.request.method != 'GET'})
        return kwargs

    def form_valid(self, form: FormGeneratorForm):
        form.save()
        messages.success(self.request, self.object.success_message or _("Form submited successfully."), 'success')
        if self.request.htmx:
            return HttpResponseClientRedirect(self.get_success_url())
        return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self, form):
        messages.success(self.request, str(form.errors), 'danger')
        return super().form_invalid(form)
