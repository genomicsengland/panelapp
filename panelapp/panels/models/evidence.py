from django.db import models
from django.utils.functional import cached_property
from model_utils.models import TimeStampedModel
from accounts.models import Reviewer


class Evidence(TimeStampedModel):
    class Meta:
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['rating']),
        ]

    HIGH_CONFIDENCE_SOURCES = [
        "Radboud University Medical Center, Nijmegen",
        "Illumina TruGenome Clinical Sequencing Services",
        "Emory Genetics Laboratory",
        "UKGTN",
    ]

    OTHER_SOURCES = [
        "Other",
        "Expert list",
        "Expert Review",
        "Literature",
        "Eligibility statement prior genetic testing",
        "Research"
    ]

    ALL_SOURCES = HIGH_CONFIDENCE_SOURCES + OTHER_SOURCES

    EXPERT_REVIEWS = {
        "Expert Review Green": 4,
        "Expert Review Amber": 2,
        "Expert Review Red": 1,
        "Expert Review Removed": 0
    }

    name = models.CharField(max_length=255)
    rating = models.IntegerField()
    comment = models.CharField(max_length=255)

    reviewer = models.ForeignKey(Reviewer, null=True, on_delete=models.PROTECT)
    legacy_type = models.CharField(max_length=255, null=True)

    def __str__(self):
        return self.name

    @cached_property
    def type(self):
        """
        In the first version we didn't save reviewer for the evidence, just user type.
        This version checks if reviewer is set and returns this reviewer user type,
        otherwise we take legacy data which is migrated from V1.
        """

        if self.reviewer:
            return self.reviewer.user_type
        else:
            return self.legacy_type

    @cached_property
    def is_GEL(self):
        return self.type == Reviewer.TYPES.GEL

    def dict_tr(self):
        return {
            "name": self.name,
            "comment": self.comment,
            "rating": self.rating,
            "date": self.created,
            "type": self.type
        }
