from django.db import models
from model_utils.models import TimeStampedModel


class Evidence(TimeStampedModel):
    source_name = models.CharField(max_length=255)
    rating = models.IntegerField()
    comment = models.CharField(max_length=255)
    type = models.CharField(max_length=255)

    def dict_tr(self):
        return {
            "name": self.source_name,
            "comment": self.comment,
            "rating": self.rating,
            "date": self.created,
            "type": self.type
        }
