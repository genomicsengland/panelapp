from django.db import models
from django.db.postgres.fields import ArrayField

from .level4title import Level4Title


class Panel(models.Model):
    major_version = models.IntegerField()
    minor_version = models.IntegerField()
    level4title = models.ForeignKey(Level4Title)
    #panellist = ListField(EmbeddedModelField(GPEntry_bck)) # check and remove
    panel_name = models.CharField(max_length=255) # remove
    approved = BooleanField()
    version_comment = models.CharField(max_length=2555, null=True)
    old_panels = ArrayField(models.CharField(max_length=255))

    # move these to properties
    number_of_genes = models.IntegerField(null=True,  blank=True,)
    number_of_evaluated_genes = models.IntegerField(null=True,  blank=True,)
    number_of_reviewers = models.IntegerField(null=True,  blank=True,)
    number_of_green_rating = models.IntegerField(null=True,  blank=True,)
    number_of_red_rating = models.IntegerField(null=True,  blank=True,)
    number_of_amber_rating = models.IntegerField(null=True,  blank=True,)
