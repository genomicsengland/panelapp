from django.db import models
from django.db.models import Count
from django.db.models import Subquery
from django.contrib.postgres.fields import ArrayField
from model_utils.models import TimeStampedModel

from .genepanel import GenePanel
from .level4title import Level4Title


class GenePanelSnapshotManager(models.Manager):
    def get_latest_ids(self):
        return super().get_queryset()\
            .distinct('panel')\
            .values('pk')\
            .order_by('panel', '-major_version', '-minor_version')

    def get_active(self):
        return super().get_queryset()\
            .prefetch_related('panel', 'level4title')\
            .filter(pk__in=Subquery(self.get_latest_ids()))\
            .annotate(
                number_of_reviewers=Count('genepanelentrysnapshot__evaluation__user', distinct=True),
                number_of_evaluated_genes=Count('genepanelentrysnapshot__evaluation'),
                number_of_genes=Count('genepanelentrysnapshot'),
            )\
            .order_by('panel', '-major_version', '-minor_version')


class GenePanelSnapshot(TimeStampedModel):
    class Meta:
        get_latest_by = "created"
        ordering = ['-created', '-major_version', '-minor_version']

    objects = GenePanelSnapshotManager()

    level4title = models.ForeignKey(Level4Title)
    panel = models.ForeignKey(GenePanel)
    major_version = models.IntegerField(default=0)
    minor_version = models.IntegerField(default=0)
    version_comment = models.TextField(null=True)
    old_panels = ArrayField(models.CharField(max_length=255))

    def increment_version(self, major=False, commit=True):
        if major:
            self.major_version += 1
            self.minor_version = 0
        else:
            self.minor_version += 1

        if commit:
            self.save()

    def get_form_initial(self):
        return {
            "level4": self.level4title.name,
            "level2": self.level4title.level2title,
            "level3": self.level4title.level3title,
            "description": self.level4title.description,
            "omim": ", ".join(self.level4title.omim),
            "orphanet": ", ".join(self.level4title.orphanet),
            "hpo": ", ".join(self.level4title.hpo),
            "old_panels": ", ".join(self.old_panels)
        }

    def get_all_entries(self):
        pass

    """
    # move these to properties
    number_of_green_rating = models.IntegerField(null=True,  blank=True,)
    number_of_red_rating = models.IntegerField(null=True,  blank=True,)
    number_of_amber_rating = models.IntegerField(null=True,  blank=True,)
    """
