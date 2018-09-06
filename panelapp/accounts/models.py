from base64 import b64decode, b64encode
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import BaseUserManager
from django.core import signing
from django.conf import settings
from django.urls import reverse
from django.db.models.signals import post_save
from django.dispatch import receiver
from rest_framework.authtoken.models import Token

from model_utils import Choices
from model_utils.models import TimeStampedModel

from .tasks import revierwer_confirmed_email
from .tasks import send_verification_email


class UserManager(BaseUserManager):
    def panel_contributors(self, panel_id):
        return super().get_queryset()\
            .distinct('pk')\
            .filter(evaluation__genepanelentrysnapshot__panel__pk=panel_id)\
            .prefetch_related('reviewer')

    def _create_user(self, username, email, password, **extra_fields):
        """
        Create and save a user with the given username, email, and password.
        """
        if not username:
            raise ValueError('The given username must be set')
        email = self.normalize_email(email)
        username = self.model.normalize_username(username)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(username, email, password, **extra_fields)

    def create_superuser(self, username, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(username, email, password, **extra_fields)

    def get_by_base64_email(self, base64_email):
        return super().get_queryset().get(email=b64decode(base64_email).decode())


class User(AbstractUser, TimeStampedModel):
    objects = UserManager()

    @property
    def base64_email(self):
        assert self.email
        return b64encode(self.email.encode()).decode()

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

    def get_recent_evaluations(self):
        return self.evaluation_set.prefetch_related('genepanelentrysnapshot_set')[:35]

    def get_crypto_id(self):
        """Returns HMAC signed base64 string of JSON with current object id

        :return: HMAC signed string
        """

        assert self.pk
        return signing.dumps({'id': self.pk})

    def verify_crypto_id(self, payload):
        """Check if payload contains the same PK as this object.

        :param payload: HMAC signed string
        :return: True if payload is valid (with respect to max age), False otherwise
        """
        try:
            return self.pk and signing.loads(payload, max_age=settings.ACCOUNT_EMAIL_VERIFICATION_PERIOD)\
                .get('id', None) == self.pk
        except (signing.SignatureExpired, signing.BadSignature):
            return False

    def get_email_verification_url(self):
        return reverse('accounts:verify_email', kwargs={
            'b64_email': self.base64_email,
            'crypto_id': self.get_crypto_id()
        })

    def send_verification_email(self):
        send_verification_email.delay(self.pk)

    def activate(self):
        """Mark user as active

        :return: None
        """
        self.is_active = True
        self.save(update_fields=['is_active', ])


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

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    user_type = models.CharField(max_length=255, choices=TYPES, default=TYPES.EXTERNAL)
    affiliation = models.CharField(max_length=1024)
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


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    if created:
        Token.objects.create(user=instance)
