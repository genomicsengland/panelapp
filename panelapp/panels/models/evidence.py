from django.db import models


class Evidence(models.Model):
    name = models.CharField(max_length=255)
    rating = models.IntegerField()
    comment = models.CharField(max_length=255)
    date = models.DateTimeField()
    type = models.CharField(max_length=255)

    def dict_tr(self):
        return {
            "name": self.name,
            "comment": self.comment,
            "rating": self.rating,
            "date": self.date,
            "type": self.type
        }
