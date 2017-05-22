from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import BaseUserManager

from model_utils import Choices
from model_utils.models import TimeStampedModel


class User(AbstractUser, TimeStampedModel):
    pass


class Reviewer(models.Model):
    TYPES = Choices(
        'GEL',
        'EXTERNAL',
        'REVIEWER'
    )
    ROLES = Choices(
        "Clinical Scientist",
        "Clinician",
        "Genome analyst",
        "Genetic Counsellor",
        "Bioinformatician",
        "Industry",
        "Lab director",
        "Principal Investigator",
        "Technician",
        "Researcher",
        "Student",
        "Other"
    )
    WORKPLACES = Choices(
        "Research lab",
        "NHS diagnostic lab",
        "Other diagnostic lab",
        "NHS clinical service",
        "Other clinical service",
        "Industry",
        "Other",
    )
    GROUPS = Choices(
        "GeCIP domain",
        "GENE consortium member",
        "NHS Genomic Medicine Centre",
        "Other NHS organisation",
        "Other biotech or pharmaceutical",
        "Other",
    )

    user = models.OneToOneField(User)
    user_type = models.CharField(max_length=255, choices=TYPES, default=TYPES.EXTERNAL)
    affiliation = models.CharField(max_length=255)
    workplace = models.CharField(max_length=255, choices=WORKPLACES)
    role = models.CharField(max_length=255, choices=ROLES)
    group = models.CharField(max_length=255, choices=GROUPS)

    def __str__(self):
        return str(self.user)

    def is_GEL(self):
        return True if self.user_type == "GEL" else False

    def is_REVIEWED(self):
        return True if self.user_type == "REVIEWED" else False

    def is_reviewd(self):
        return True if self.is_GEL() or self.is_REVIEWED() else False
