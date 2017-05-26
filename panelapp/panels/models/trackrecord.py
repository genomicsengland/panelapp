from django.db import models
from model_utils.models import TimeStampedModel

from accounts.models import User


class TrackRecord(TimeStampedModel):
    """
    This needs to be refactored. How TrackRecords are different to Activities?
    """

    issue_type = models.CharField(max_length=255) # can this be standartized?
    issue_description = models.CharField(max_length=255)
    user = models.ForeignKey(User)

    # get the following via the user
    #user = models.CharField(max_length=255)
    #gel_status = models.IntegerField()
    #curator_status = models.IntegerField()

    def dict_tr(self):
        return {
            "date": self.created,
            "gel_status": self.gel_status,
            "curator_status": self.curator_status,
            "issue_type": self.issue_type,
            "issue_description": self.issue_description,
            "user": self.user
        }
