import uuid
from django.contrib import admin
from django.utils.text import slugify
from django.urls import reverse
from django.utils.safestring import mark_safe

from form_generator import const
from form_generator.forms import FieldForm, FormAdminForm
from form_generator.models import (
    FieldCategory,
    Form,
    Field,
    FormFieldThrough,
    Value,
    FormResponse,
    FormAPIThrough,
    FieldValueThrough,
    FormAPIManager,
)

# Register your models here.


class FormFieldThroughInlineAdmin(admin.TabularInline):
    model = FormFieldThrough
    extra = 1
    raw_id_fields = ("field",)


class FormAPIThroughInlineAdmin(admin.TabularInline):
    model = FormAPIThrough
    extra = 1
    raw_id_fields = ("api",)


@admin.register(Form)
class FormAdmin(admin.ModelAdmin):
    inlines = [FormFieldThroughInlineAdmin, FormAPIThroughInlineAdmin]
    form = FormAdminForm
    actions = ("clone_action",)

    def clone_action(self, request, queryset):
        for obj in queryset:
            detail = obj.detail
            apis = obj.apis.all()
            fields = obj.fields.all()
            for field in obj._meta.local_fields:
                if field.unique:
                    if field.name in ("pk", "id"):
                        setattr(obj, field.name, None)
                    setattr(obj, "slug", uuid.uuid4())

            setattr(obj, "status", const.FormStatus.DRAFT)
            obj.save()

            for field in fields:
                field = FormFieldThrough.objects.create(form=obj, field=field)
            for api in apis:
                api = FormAPIThrough.objects.create(form=obj, api=api)

            setattr(detail, "pk", None)
            setattr(detail, "form_id", obj.id)
            detail.save()


class FieldValueThroughInlineAdmin(admin.TabularInline):
    model = FieldValueThrough
    extra = 1
    raw_id_fields = ("value",)


@admin.register(Field)
class FieldAdmin(admin.ModelAdmin):
    inlines = [FieldValueThroughInlineAdmin]
    readonly_fields = ["name"]
    form = FieldForm

    def save_form(self, request, form, change):
        form.instance.name = slugify(form.instance.label, True).replace("-", "_")
        return super().save_form(request, form, change)


@admin.register(FormResponse)
class FormResponseAdmin(admin.ModelAdmin):
    list_display = ["id", "get_form_title", "user_ip", "show_response"]
    list_display_links = ["id", "get_form_title"]

    @admin.display(description="Form Title")
    def get_form_title(self, obj):
        return obj.form.title

    @admin.display(description="Response")
    def show_response(self, obj):
        return mark_safe(
            f"<a href='{reverse('form_generator:form_response', args=(obj.id, ))}'>Response</a>"
        )


admin.site.register(Value)
admin.site.register(FormAPIManager)
admin.site.register(FieldCategory)
