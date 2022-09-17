from django.db import models
from django.utils import timezone

from core import consts

class FormDetailQuerySet(models.QuerySet):

    def filter_valid(self):
        current_date = timezone.now()
        return self.filter(form__status=consts.FormStatus.PUBLISH).\
            filter(models.Q(limit_to__gt=0) | models.Q(limit_to__isnull=True)).\
            filter((models.Q(valid_from__lte=current_date) | models.Q(valid_from__isnull=True)) & 
                    (models.Q(valid_to__gte=current_date) | models.Q(valid_to__isnull=True)))


class FormDetailManager(models.Manager):

    def get_queryset(self) -> FormDetailQuerySet:
        return FormDetailQuerySet(model=self.model, using=self._db)

    def filter_valid(self):
        return self.get_queryset().filter_valid()