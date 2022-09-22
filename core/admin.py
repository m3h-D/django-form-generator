import uuid
from django.contrib import admin
from django.utils.text import slugify

from core import consts
from core.forms import FormTemplateForm
from core.models import FieldCategory, Form, Field, FormFieldThrough, FormTemplate, Value, FormResponse, FormAPIThrough, FieldValueThrough, FormAPIManager
# Register your models here.

class FormFieldThroughInlineAdmin(admin.TabularInline):
    model = FormFieldThrough
    extra = 1
    raw_id_fields = ('field',)

class FormAPIThroughInlineAdmin(admin.TabularInline):
    model = FormAPIThrough
    extra = 1
    raw_id_fields = ('api',)

@admin.register(Form)
class FormAdmin(admin.ModelAdmin):
    inlines = [FormFieldThroughInlineAdmin, FormAPIThroughInlineAdmin]

    actions = ('clone_action', )

    def clone_action(self, request, queryset):
        for obj in queryset:
            detail = obj.detail
            apis = obj.apis.all()
            fields = obj.fields.all()
            for field in obj._meta.local_fields:
                if field.unique:
                    if field.name in ('pk', 'id'):
                        setattr(obj, field.name, None)
                    setattr(obj, 'slug', uuid.uuid4())

            setattr(obj, 'status', consts.FormStatus.DRAFT)
            obj.save()

            for field in fields:
                field = FormFieldThrough.objects.create(form=obj, field=field)
            for api in apis:
                api = FormAPIThrough.objects.create(form=obj, api=api)

            setattr(detail, 'pk', None)
            setattr(detail, 'form_id', obj.id)
            detail.save()


class FieldValueThroughInlineAdmin(admin.TabularInline):
    model = FieldValueThrough
    extra = 1
    raw_id_fields = ('value',)


@admin.register(Field)
class FieldAdmin(admin.ModelAdmin):
    inlines = [FieldValueThroughInlineAdmin]
    readonly_fields = ['name']

    def save_form(self, request, form, change):
        form.instance.name = slugify(form.instance.label, True).replace('-', '_')
        return super().save_form(request, form, change)


@admin.register(FormTemplate)
class TemplateFormAdmin(admin.ModelAdmin):
    form = FormTemplateForm


admin.site.register(FormResponse)
admin.site.register(Value)
admin.site.register(FormAPIManager)
admin.site.register(FieldCategory)