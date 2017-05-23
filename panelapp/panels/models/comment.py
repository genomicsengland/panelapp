from django.db import models


class Comment(models.Model):
    date = models.DateTimeField()
    comment = models.CharField(max_length=2555)

    def dict_tr(self):
        return {
            "date": self.date,
            "comment": self.comment
        }

    def __eq__(self, other):
        if self.comment == other.comment:
            return True
        else:
            return False
