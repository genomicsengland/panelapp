from django.db import models
from django.db.models import Count
from django.utils.functional import cached_property
from model_utils.models import TimeStampedModel


class GenePanel(TimeStampedModel):
    name = models.CharField(max_length=255)
    approved = models.BooleanField(default=False)
    promoted = models.BooleanField(default=False)

    def __str__(self):
        ap = self.active_panel
        return "{} version {}.{}".format(self.name, ap.major_version, ap.minor_version)

    def approve(self):
        self.approved = True
        self.save()

    def reject(self):
        self.approved = False
        self.save()

    @cached_property
    def active_panel(self):
        return self.genepanelsnapshot_set\
            .prefetch_related('panel', 'level4title')\
            .annotate(
                number_of_reviewers=Count('genepanelentrysnapshot__evaluation__user', distinct=True),
                number_of_evaluated_genes=Count('genepanelentrysnapshot__evaluation'),
                number_of_genes=Count('genepanelentrysnapshot'),
            )\
            .order_by('-created', '-major_version', '-minor_version')\
            .first()
