from django.db import models
from django.utils.functional import cached_property
from model_utils.models import TimeStampedModel


class GenePanel(TimeStampedModel):
    name = models.CharField(max_length=255)
    approved = models.BooleanField(default=False)
    promoted = models.BooleanField(default=False)

    def __str__(self):
        ap = self.active_panel
        return "{} version {}.{}".format(self.name, ap.major_version, ap.minor_version)

    @cached_property
    def active_panel(self):
        return self.genepanelsnapshot_set.get_active().first()
