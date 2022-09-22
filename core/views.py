from django.shortcuts import render
from django.views.generic import DetailView
from django.views.generic.edit import FormMixin
from django.contrib import messages
from django.utils.translation import gettext as _
from django.http import HttpResponseRedirect

from django_htmx.http import HttpResponseClientRedirect
# Create your views here.

from common.utils import get_client_ip
from core.models import Form, FormResponse
from core.forms import FormGeneratorForm


def home_page(request):
    return render(request, 'base.html', {})


class FormGeneratorView(FormMixin, DetailView):
    queryset = Form.objects.filter_valid()
    model = Form
    template_name = "core/form.html"
    form_class = FormGeneratorForm

    def get_success_url(self) -> str:
        return self.object.redirect_url or self.request.META.get("HTTP_REFERER") # type: ignore

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        if form.is_valid():
            messages.success(self.request, self.object.success_message or _("Form submited successfully."), 'success')
            return self.form_valid(form)
        else:
            messages.success(self.request, str(form.errors), 'danger')
            return self.form_invalid(form)

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        self.object.call_pre_apis({'request': request})
        return response

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"request": self.request,
                        "instance": self.object,
                        "user_ip": get_client_ip(self.request), 
                        })
        return kwargs

    def form_valid(self, form: FormGeneratorForm):
        form.save()
        if self.request.htmx:
            return HttpResponseClientRedirect(self.get_success_url())
        return HttpResponseRedirect(self.get_success_url())


class FormResponseView(FormMixin, DetailView):
    queryset = FormResponse.objects.all()
    model = FormResponse
    template_name = "core/form_response.html"
    form_class = FormGeneratorForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"request": self.request,
                        "instance": self.object.form,
                        "form_response": self.object,
                        "user_ip": get_client_ip(self.request), 
                        })
        return kwargs