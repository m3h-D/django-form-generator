from django.views.generic import DetailView
from django.views.generic.edit import FormMixin
from django.contrib import messages
from django.utils.translation import gettext as _

from django_htmx.http import HttpResponseClientRedirect

from django_form_generator.common.utils import get_client_ip
from django_form_generator.models import Form
from django_form_generator.forms import FormGeneratorForm
from django_form_generator.settings import form_generator_settings as fg_settings


class FormGeneratorView(FormMixin, DetailView):
    queryset = Form.objects.filter_valid()
    model = Form
    template_name = "django_form_generator/form.html"

    def get_queryset(self):
        """Allow preview for superuser and staff members"""
        if getattr(self.request.user, "is_staff", False) or getattr(self.request.user, "is_superuser", False):
            return Form.objects.all()
        return super().get_queryset()

    def get_form_class(self):
        return fg_settings.FORM_GENERATOR_FORM

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
        return HttpResponseClientRedirect(self.get_success_url())


class FormResponseView(FormMixin, DetailView):
    queryset = fg_settings.FORM_GENERATOR_RESPONSE_MODEL.objects.all()
    model = fg_settings.FORM_GENERATOR_RESPONSE_MODEL
    template_name = 'django_form_generator/form_response.html'
    slug_url_kwarg = 'unique_id'
    slug_field = 'unique_id'


    def get_form_class(self):
        return fg_settings.FORM_RESPONSE_FORM

    def get_success_url(self) -> str:
        return self.object.form.redirect_url or self.request.META.get("HTTP_REFERER")  # type: ignore

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        if form.is_valid():
            messages.success(
                self.request,
                self.object.form.success_message or _("Form submited successfully."),
                "success",
            )
            return self.form_valid(form)
        else:
            messages.success(self.request, str(form.errors), "danger")
            return self.form_invalid(form)

    def form_valid(self, form):
        form.save()
        return super().form_valid(form)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update(
            {
                "form": self.object.form,
                "form_response": self.object,
                "request": self.request
            }
        )
        return kwargs
