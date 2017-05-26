from django.db import models
from django.db.models import Prefetch
from model_utils.models import TimeStampedModel


class GenePanel(TimeStampedModel):
    name = models.CharField(max_length=255)
    approved = models.BooleanField(default=False)
    promoted = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    @property
    def active_panel(self):
        return self.genepanelsnapshot_set.first()
