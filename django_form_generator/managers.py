from django.db import models
from django.utils import timezone

from django_form_generator import const
from django_form_generator.settings import form_generator_settings as fg_settings

class FormQuerySet(models.QuerySet):

    def filter_valid(self) -> models.QuerySet:
        current_date = timezone.now()
        related_name = f'{fg_settings.FORM_GENERATOR_RESPONSE_MODEL._meta.model_name}_responses'
        lookup = self.annotate(c_forms=models.Count(related_name)).filter(status=const.FormStatus.PUBLISH).\
            filter(models.Q(limit_to__gt=models.F('c_forms')) | models.Q(limit_to__isnull=True)).\
            filter((models.Q(valid_from__lte=current_date) | models.Q(valid_from__isnull=True)) & 
                    (models.Q(valid_to__gte=current_date) | models.Q(valid_to__isnull=True)))
        return lookup


class FormManager(models.Manager):

    def get_queryset(self) -> FormQuerySet:
        return FormQuerySet(model=self.model, using=self._db)

    def filter_valid(self):
        return self.get_queryset().filter_valid()