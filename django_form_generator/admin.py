import uuid
from django.http import JsonResponse
from django.contrib import admin
from django.utils.text import slugify
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _
from django.db.transaction import atomic

from django_form_generator import const
from django_form_generator.common.admins import FormFilter, AdminMixin
from django_form_generator.common.utils import FilterMixin
from django_form_generator.forms import FieldForm, FormAdminForm, FormResponseFilterForm, ValidatorAdminForm
from django_form_generator.models import (
    FieldCategory,
    Form,
    Field,
    FieldValidator,
    FormFieldThrough,
    Option,
    FormResponse,
    FormAPIThrough,
    FieldOptionThrough,
    FormAPIManager,
)


class FormResponseFilter(FilterMixin, FormFilter):

    template = "django_form_generator/filters/form_response_filter.html"
    form_class = FormResponseFilterForm
    title = _('Search on data')
    parameter_name = 'data'

    def get_parameters(self, request) -> list[str]:
        params = []
        for param in self.expected_parameters():
            url_param = self.clean_parameters(request.GET.getlist(param))
            if param == f'{self.field.name}-form_id':
                params.append(self.request.GET.get(param))
            else:
                params.append(url_param)
        return params
    
    def queryset(self, request, queryset):
        response_filters, response_annotations = self.get_lookups(request)
        return queryset.alias(**response_annotations).filter(response_filters)

    def expected_parameters(self):
        return [f'{self.field.name}-form_id', f'{self.field.name}-field', f'{self.field.name}-field_lookup', f'{self.field.name}-operand', f'{self.field.name}-value']


class FormFieldThroughInlineAdmin(admin.TabularInline):
    model = FormFieldThrough
    extra = 1
    raw_id_fields = ("field",)
    verbose_name = _('Field')
    verbose_name_plural = _('Fields')


class FormAPIThroughInlineAdmin(admin.TabularInline):
    model = FormAPIThrough
    extra = 1
    raw_id_fields = ("api",)
    verbose_name = _('API')
    verbose_name_plural = _('APIs')


@admin.register(Form)
class FormAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'status', 'get_style', 'created_at', 'updated_at']
    list_display_links = ['id', 'title']
    list_editable = ['status']
    list_filter = ['status', 'created_at']
    search_fields = ['title', 'slug']
    search_help_text = 'Search on Title & Slug'
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
            'fields': ('style', 'direction'),
        }),
        ('Limitations', {
            'classes': ('wide',),
            'fields': ('limit_to', 'valid_from', 'valid_to', 'is_editable'),
        }),
    )

    @admin.display(description="Style")
    def get_style(self, obj):
        if obj.style:
            return const.FormStyle(obj.style).label

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

class FieldOptionThroughInlineAdmin(admin.TabularInline):
    model = FieldOptionThrough
    extra = 1
    raw_id_fields = ("option",)
    verbose_name = _('Option')
    verbose_name_plural = _('Options')


class FieldValidatorThroughInlineAdmin(admin.TabularInline):
    model = FieldValidator
    form = ValidatorAdminForm
    extra = 1
    verbose_name = _('Validator')
    verbose_name_plural = _('Validators')

@admin.register(Field)
class FieldAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'genre', 'is_active', 'is_required', 'read_only', 'write_only', 'created_at', 'updated_at']
    list_display_links = ['id', 'name']
    list_editable = ['is_active', 'is_required']
    list_filter = ['is_active', 'is_required', 'read_only', 'write_only', 'created_at', 'genre']
    search_fields = ['label', 'name', 'forms__title']
    search_help_text = 'Search on Label & Name & Form title'
    inlines = [FieldOptionThroughInlineAdmin, FieldValidatorThroughInlineAdmin]
    readonly_fields = ['id', 'created_at', 'updated_at']
    form = FieldForm
    prepopulated_fields = {'name': ('label',), }
    fieldsets = (
        (None, {
            'fields': ('label', 'name', 'genre', 'is_required', 'placeholder', 'default', 'help_text', 'is_active', 'read_only', 'write_only', 'id', 'created_at', 'updated_at')
        }),
        ('Dpendency', {
            'classes': ('wide',),
            'fields': ('content_type', 'object_id'),
        }),
    )

    def save_form(self, request, form, change):
        slug = form.instance.name if form.instance.name else form.instance.label
        form.instance.name = slugify(slug, True).replace("-", "_").replace(" ", "_")
        return super().save_form(request, form, change)


@admin.register(FormResponse)
class FormResponseAdmin(AdminMixin, admin.ModelAdmin):
    list_display = ["id", "get_form_title", "user_ip", "show_response"]
    list_display_links = ["id", "get_form_title"]
    list_filter = [('data', FormResponseFilter)]
    search_fields = ['form__title', 'form__slug', 'unique_id']
    search_help_text = 'Search on Form title & Form slug & unique_id'
    readonly_fields = ['id', 'unique_id', 'created_at', 'updated_at']
    extra_views = [
        ('fetch_options', 'options/<int:field_id>'),
        ('fetch_fields', 'fields/<int:form_id>')
        ]


    @admin.display(description="Form Title")
    def get_form_title(self, obj):
        return obj.form.title

    @admin.display(description="Response")
    def show_response(self, obj):
        return mark_safe(
            f"<a href='{reverse('django_form_generator:form_response', args=(obj.unique_id, ))}'>Response</a>"
        )
    
    def fetch_options(self, request, field_id: int):
        options = {}
        field = Field.objects.get(id=field_id)
        if field.genre in (const.FieldGenre.selectable_fields()):
            options = Option.objects.filter(fields__id=field_id).values('id', 'name')
        return JsonResponse(list(options), safe=False)
    
    def fetch_fields(self, request, form_id: int):
        fields = Form.objects.get(id=form_id).get_fields().values('id', 'label')
        return JsonResponse(list(fields), safe=False)

        
@admin.register(FormAPIManager)
class FormAPIManagerAdmin(admin.ModelAdmin):
    list_display = ["id", "title", "method", "execute_time", "is_active", "cache_by", "created_at", "updated_at"]
    list_display_links = ["id", "title"]
    list_filter = ['is_active', 'created_at', 'execute_time', 'method']
    list_editable = ['is_active']
    search_fields = ['title', 'forms__title', 'forms__slug']
    search_help_text = 'Search on Title & Form title & Form slug'
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(FieldCategory)
class FieldCategoryAdmin(admin.ModelAdmin):
    list_display = ["id", "title", "parent", "weight", "is_active", "created_at", "updated_at"]
    list_display_links = ["id", "title"]
    list_filter = ['is_active', 'created_at', ('parent', admin.filters.EmptyFieldListFilter)]
    list_editable = ['is_active']
    search_fields = ['title']
    search_help_text = 'Search on Title'
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(Option)
class OptionAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "is_active", "created_at", "updated_at"]
    list_display_links = ["id", "name"]
    list_filter = ['is_active', 'created_at']
    list_editable = ['is_active']
    search_fields = ['name', 'fields__name', 'fields__label']
    search_help_text = 'Search on Name & Field name & Field label'
    readonly_fields = ['id', 'created_at', 'updated_at']

