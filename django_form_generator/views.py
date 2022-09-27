from django.views.generic import DetailView
from django.views.generic.edit import FormMixin
from django.contrib import messages
from django.utils.translation import gettext as _
from django.http import HttpResponseRedirect
from django.utils.module_loading import import_string
from django.conf import settings

from django_htmx.http import HttpResponseClientRedirect

from django_form_generator.common.utils import get_client_ip
from django_form_generator.models import Form, FormResponse
from django_form_generator.forms import FormGeneratorForm


class FormGeneratorView(FormMixin, DetailView):
    queryset = Form.objects.filter_valid()
    model = Form
    template_name = "django_form_generator/form.html"

    def get_form_class(self):
        return import_string(settings.FORM_GENERATOR_FORM)

    def get_success_url(self) -> str:
        return self.object.redirect_url or self.request.META.get("HTTP_REFERER")  # type: ignore

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        if form.is_valid():
            messages.success(
                self.request,
                self.object.success_message or _("Form submited successfully."),
                "success",
            )
            return self.form_valid(form)
        else:
            messages.success(self.request, str(form.errors), "danger")
            return self.form_invalid(form)

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        self.object.call_pre_apis({"request": request})
        return response

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update(
            {
                "request": self.request,
                "form": self.object,
                "user_ip": get_client_ip(self.request),
            }
        )
        return kwargs

    def form_valid(self, form: FormGeneratorForm):
        form.save()
        if self.request.htmx:
            return HttpResponseClientRedirect(self.get_success_url())
        return HttpResponseRedirect(self.get_success_url())


class FormResponseView(FormMixin, DetailView):
    queryset = FormResponse.objects.all()
    model = FormResponse
    template_name = "django_form_generator/form_response.html"

    def get_form_class(self):
        return import_string(settings.FORM_GENERATOR_RESPONSE_FORM)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update(
            {
                "form": self.object.form,
                "form_response": self.object,
            }
        )
        return kwargs
