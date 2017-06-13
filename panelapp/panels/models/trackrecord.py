from django.db import models
from model_utils import Choices
from model_utils.models import TimeStampedModel

from accounts.models import User


class TrackRecord(TimeStampedModel):
    """
    TODO @migrate issue_types need to be migrated
    """

    ISSUE_TYPES = Choices(
        ("Created", "Created"),
        ("NewSource", "Added New Source"),
        ("ChangedGeneName", "Changed Gene Name"),
        ("SetPhenotypes", "Set Phenotypes"),
        ("SetModelofInheritance", "Set Model of Inheritance"),
        ("ClearSources", "Clear Sources"),
        ("SetModeofPathogenicity", "Set mode of pathogenicity"),
        ("GeneClassifiedbyGenomicsEnglandCurator", "Gene classified by Genomics England curator"),
        ("SetModeofInheritance", "Set mode of inheritance"),
        ("SetPhenotypes", "Set phenotypes"),
        ("SetPublications", "Set publications"),
    )

    class Meta:
        ordering = ('-created',)

    issue_type = models.CharField(choices=ISSUE_TYPES, max_length=512)  # can this be standartized?
    issue_description = models.TextField()
    user = models.ForeignKey(User)
    curator_status = models.IntegerField(default=0)  # Boolean maybe?
    gel_status = models.IntegerField(default=0)

    def dict_tr(self):
        return {
            "date": self.created,
            "gel_status": self.gel_status,
            "curator_status": self.curator_status,
            "issue_type": self.issue_type,
            "issue_description": self.issue_description,
            "user": self.user
        }
