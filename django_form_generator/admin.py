import uuid
from django.db import models
from django.contrib import admin
from django.utils.text import slugify
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.transaction import atomic

from django_form_generator import const
from django_form_generator.common.admins import FormFilter
from django_form_generator.forms import FieldForm, FormAdminForm, FormResponseFilterForm
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




class FormResponseFilter(FormFilter):

    template = "django_form_generator/filters/form_response_filter.html"
    form_class = FormResponseFilterForm

    def _create_related_fields_lookup(self, q, fields, fields_text, current_index, current_field_id, related_field_id, index=None):
        related =  Field.objects.filter(object_id=related_field_id, content_type__model='field').last()
        if related and str(related.pk) in fields:
            depended_field = Field.objects.filter(object_id=current_field_id, content_type__model='field').last()
            if depended_field:
                try:
                    depended_field_index = current_index + 1
                    fields_text[depended_field_index]
                except IndexError:
                    depended_field_index = current_index 
                dp_value = int(fields_text[depended_field_index]) if fields_text[depended_field_index].isdigit() else fields_text[depended_field_index]
                if index:
                    if isinstance(dp_value, int):
                        q.add(models.Q(**{f"{self.field_path}__{index}__value": dp_value}), models.Q.AND)
                    else:
                        q.add(models.Q(**{f"{self.field_path}__{index}__value__regex": dp_value}), models.Q.AND)
                else:
                    q.add(models.Q(**{f"{self.field_path}__contains": [{"id": depended_field.pk, "value": dp_value}]}), models.Q.AND)
        return q

    def get_lookups(self):
        lookup = models.Q()

        fields_text = self.request.GET.getlist(f'{self.field.name}-text')
        fields_id = self.request.GET.getlist(f'{self.field.name}-field')
        fields_operand = self.request.GET.getlist(f'{self.field.name}-operand')
        form_id = self.request.GET.get(f'{self.field.name}-form_id')
        if form_id:
            form = Form.objects.prefetch_related('fields').get(id=int(form_id))
            form_fields_list = list(form.get_fields().values_list('id', flat=True))

            for i in range(len(fields_text)):
                field_id = int(fields_id[i])
                field_value = int(fields_text[i]) if fields_text[i].isdigit() else fields_text[i]
                current_operand = getattr(models.Q, fields_operand[i], models.Q.AND)
                if isinstance(field_value, int):
                    lookup_content = "{0}__{1}__value"
                else:
                    lookup_content = "{0}__{1}__value__regex"
                try:
                    index = form_fields_list.index(field_id)
                    inner_lookup = models.Q(**{lookup_content.format(self.field_path, index): field_value})
                    self._create_related_fields_lookup(inner_lookup, fields_id, fields_text, i, field_id, field_id, index+1)
                    lookup.add(inner_lookup, current_operand)
                except ValueError:
                    # searching on multi_fields
                    inner_lookup = models.Q()
                    current_field = Field.objects.get(id=field_id)
                    multi_fields = Field.objects.filter(name__startswith=current_field.name).order_by('name')
                    if multi_fields.count() > 1:
                        for field_ in multi_fields[1:]:
                            index = form_fields_list.index(field_.pk)
                            related_lookup = models.Q(**{lookup_content.format(self.field_path, index): field_value})
                            self._create_related_fields_lookup(related_lookup, fields_id, fields_text, i, field_.pk, multi_fields[0].pk, index+1)
                            inner_lookup.add(related_lookup, models.Q.OR)
                        lookup.add(inner_lookup, current_operand)
        return lookup


    def form_lookups(self):
        name = self.field.name
        return (
            ("%s-form_id" % name, "%s__exact" % name),
            ("%s-field" % name, "%s__contains" % name),
            ("%s-text" % name, "%s__contains" % name),
            ("%s-operand" % name, "%s__contains" % name),
        )


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
    list_filter = [('data', FormResponseFilter)]
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

