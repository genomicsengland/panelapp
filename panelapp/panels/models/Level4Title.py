from django.db import models
from django.contrib.postgres.fields import ArrayField


class Level4Title(models.Model):
    name = models.CharField(max_length=255)
    description = models.CharField(max_length=2555)
    level3title = models.CharField(max_length=255)
    level2title = models.CharField(max_length=255)
    omim = ArrayField(models.CharField(max_length=255))
    orphanet = ArrayField(models.CharField(max_length=255))
    hpo = ArrayField(models.CharField(max_length=255))

    def __str__(self):
        return str(self.name)

    def __eq__(self, other):
        if other == self.name:
            return True
        else:
            return False

    def dict_tr(self):
        return {"name": self.name, "description": self.description,
                "level3title": self.level3title, "level2title": self.level2title,
                "omim": self.omim, "orphanet": self.orphanet, "hpo": self.hpo}
