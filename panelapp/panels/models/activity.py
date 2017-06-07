from django.db import models
from model_utils.models import TimeStampedModel

from accounts.models import User
from .genepanel import GenePanel


class Activity(TimeStampedModel):
    panel = models.ForeignKey(GenePanel)
    gene_symbol = models.CharField(max_length=255, null=True)
    user = models.ForeignKey(User)
    text = models.CharField(max_length=255)
