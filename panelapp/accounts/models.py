from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import BaseUserManager

from model_utils.models import TimeStampedModel


class User(AbstractUser, TimeStampedModel):
    pass


class Reviewers(models.Model):
    user = models.OneToOneField(User)
    user_type = models.CharField(max_length=255)
    affiliation = models.CharField(max_length=255)
    workplace = models.CharField(max_length=255)
    role = models.CharField(max_length=255)
    group = models.CharField(max_length=255)

    def __str__(self):
        return str(self.user)

    def is_GEL(self):
        return True if self.user_type == "GEL" else False
