from django.db import models
from django.db.models import Q
from model_utils.models import TimeStampedModel

from accounts.models import User
from .genepanel import GenePanel


class ActivityManager(models.Manager):
    def visible_to_public(self):
        """Return activities for all publicly visible panels"""

        qs = self.get_queryset()
        qs = qs.filter(panel__status=GenePanel.STATUS.public)
        return qs

    def visible_to_gel(self):
        """Return activities visible to GeL curators"""

        qs = self.get_queryset()
        qs = qs.exclude(panel__status=GenePanel.STATUS.deleted)
        return qs


class Activity(TimeStampedModel):
    class Meta:
        ordering = ('-created',)

    objects = ActivityManager()

    panel = models.ForeignKey(GenePanel)
    gene_symbol = models.CharField(max_length=255, null=True)
    user = models.ForeignKey(User)
    text = models.CharField(max_length=255)
