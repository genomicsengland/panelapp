from django.db import models
from model_utils.models import TimeStampedModel

from accounts.models import User


class TrackRecord(TimeStampedModel):
    class Meta:
        ordering = ('-created',)

    issue_type = models.CharField(max_length=255)  # can this be standartized?
    issue_description = models.CharField(max_length=255)
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
