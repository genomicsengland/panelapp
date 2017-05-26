from django.db import models
from django.contrib.postgres.fields import ArrayField
from model_utils.models import TimeStampedModel

from accounts.models import User
from .comment import Comment


class Evaluation(TimeStampedModel):
    user = models.ForeignKey(User)
    rating = models.CharField(max_length=255)
    transcript = models.CharField(null=True,  blank=True, max_length=255)
    mode_of_pathogenicity = models.CharField(null=True,  blank=True, max_length=255)
    publications = ArrayField(models.CharField(null=True,  blank=True, max_length=255))
    phenotypes = ArrayField(models.CharField(null=True,  blank=True, max_length=255))
    moi = models.CharField(null=True,  blank=True, max_length=255)
    current_diagnostic = models.BooleanField(default=False)
    version = models.CharField(null=True, blank=True, max_length=255)
    comments = models.ManyToManyField(Comment)

    def dict_tr(self):
        return {
            "user": self.user,
            "rating": self.rating,
            "transcript": self.transcript,
            "moi": self.moi,
            "comments": [c.dict_tr() for c in self.comments.all()],
            "mode_of_pathogenicity": self.mode_of_pathogenicity,
            "phenotypes": self.phenotypes,
            "publications": self.publications,
            "current_diagnostic": self.current_diagnostic,
            "version": self.version,
            "date": self.created
        }
