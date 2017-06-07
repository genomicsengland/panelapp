from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import BaseUserManager

from model_utils import Choices
from model_utils.models import TimeStampedModel

from .tasks import revierwer_confirmed_email


class UserManager(BaseUserManager):
    def panel_contributors(self, panel_id):
        return super().get_queryset()\
            .distinct('pk')\
            .filter(evaluation__genepanelentrysnapshot__panel__pk=panel_id)


class User(AbstractUser, TimeStampedModel):
    objects = UserManager()

    def promote_to_reviewer(self):
        try:
            self.reviewer.user_type = Reviewer.TYPES.REVIEWER
            self.reviewer.save()
            revierwer_confirmed_email.delay(self.pk)
            return True
        except Reviewer.DoesNotExist:
            pass
        return False

    def get_reviewer_name(self):
        if self.reviewer and self.reviewer.affiliation:
            return "{} ({})".format(self.get_full_name(), self.reviewer.affiliation)
        else:
            return self.get_full_name()


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

    def is_REVIEWER(self):
        return True if self.user_type == "REVIEWER" else False

    def is_verified(self):
        return True if self.is_GEL() or self.is_REVIEWER() else False
