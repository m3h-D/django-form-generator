import uuid
from django.contrib import admin
from django.utils.text import slugify
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.transaction import atomic

from django_form_generator import const
from django_form_generator.forms import FieldForm, FormAdminForm
from django_form_generator.models import (
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
    list_display = ['id', 'title', 'status', 'get_theme', 'created_at', 'updated_at']
    list_display_links = ['id', 'title']
    list_editable = ['status']
    list_filter = ['status', 'created_at']
    search_fields = ['title', 'slug']
    readonly_fields = ['id', 'created_at', 'updated_at']
    inlines = [FormFieldThroughInlineAdmin, FormAPIThroughInlineAdmin]
    form = FormAdminForm
    actions = ("clone_action",)

    fieldsets = (
        (None, {
            'fields': ('title', 'slug', 'status', 'submit_text', 'redirect_url', 'success_message', 'id', 'created_at', 'updated_at')
        }),
        ('Style', {
            'classes': ('wide',),
            'fields': ('theme', 'direction'),
        }),
        ('Limitations', {
            'classes': ('wide',),
            'fields': ('limit_to', 'valid_from', 'valid_to', 'is_editable'),
        }),
    )

    @admin.display(description="Theme")
    def get_theme(self, obj):
        return const.FormTheme(obj.theme).label

    @atomic
    def clone_action(self, request, queryset):
        for obj in queryset:
            f_through = obj.form_field_through.all().values('field_id', 'position', 'category_id', 'weight')
            a_through = obj.form_apis.all().values('api_id', 'weight')
            for field in obj._meta.local_fields:
                if field.unique:
                    if field.name in ("pk", "id"):
                        setattr(obj, field.name, None)

            setattr(obj, "slug", uuid.uuid4())
            setattr(obj, 'title', obj.title + ' (Copy)')
            setattr(obj, "status", const.FormStatus.DRAFT)
            obj.save()

            ff_through = [FormFieldThrough(form_id=obj.id, **obj_) for obj_ in f_through]
            FormFieldThrough.objects.bulk_create(ff_through, ignore_conflicts=True)
            fa_through = [FormAPIThrough(form_id=obj.id, **obj_) for obj_ in a_through]
            FormAPIThrough.objects.bulk_create(fa_through)

class FieldValueThroughInlineAdmin(admin.TabularInline):
    model = FieldValueThrough
    extra = 1
    raw_id_fields = ("value",)


@admin.register(Field)
class FieldAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'genre', 'is_active', 'created_at', 'updated_at']
    list_display_links = ['id', 'name']
    list_editable = ['is_active']
    list_filter = ['is_active', 'created_at', 'genre']
    search_fields = ['label', 'name', 'forms__title']
    inlines = [FieldValueThroughInlineAdmin]
    readonly_fields = ['id', 'name', 'created_at', 'updated_at']
    form = FieldForm

    fieldsets = (
        (None, {
            'fields': ('label', 'genre', 'is_required', 'placeholder', 'default', 'help_text', 'is_active', 'regex_pattern', 'error_message', 'id', 'created_at', 'updated_at')
        }),
        ('File', {
            'classes': ('wide',),
            'fields': ('file_types', 'file_size'),
        }),
        ('Dpendency', {
            'classes': ('wide',),
            'fields': ('content_type', 'object_id'),
        }),
    )

    def save_form(self, request, form, change):
        form.instance.name = slugify(form.instance.label, True).replace("-", "_")
        return super().save_form(request, form, change)


@admin.register(FormResponse)
class FormResponseAdmin(admin.ModelAdmin):
    list_display = ["id", "get_form_title", "user_ip", "show_response"]
    list_display_links = ["id", "get_form_title"]
    search_fields = ['form__title', 'form__slug']
    readonly_fields = ['id', 'unique_id', 'created_at', 'updated_at']

    @admin.display(description="Form Title")
    def get_form_title(self, obj):
        return obj.form.title

    @admin.display(description="Response")
    def show_response(self, obj):
        return mark_safe(
            f"<a href='{reverse('django_form_generator:form_response', args=(obj.unique_id, ))}'>Response</a>"
        )

@admin.register(FormAPIManager)
class FormAPIManagerAdmin(admin.ModelAdmin):
    list_display = ["id", "title", "method", "execute_time", "is_active", "created_at", "updated_at"]
    list_display_links = ["id", "title"]
    list_filter = ['is_active', 'created_at', 'execute_time', 'method']
    list_editable = ['is_active']
    search_fields = ['title', 'forms__title', 'forms__slug']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(FieldCategory)
class FieldCategoryAdmin(admin.ModelAdmin):
    list_display = ["id", "title", "parent", "weight", "is_active", "created_at", "updated_at"]
    list_display_links = ["id", "title"]
    list_filter = ['is_active', 'created_at', ('parent', admin.filters.EmptyFieldListFilter)]
    list_editable = ['is_active']
    search_fields = ['title']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(Value)
class ValueAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "is_active", "created_at", "updated_at"]
    list_display_links = ["id", "name"]
    list_filter = ['is_active', 'created_at']
    list_editable = ['is_active']
    search_fields = ['name', 'fields__name', 'fields__label']
    readonly_fields = ['id', 'created_at', 'updated_at']

