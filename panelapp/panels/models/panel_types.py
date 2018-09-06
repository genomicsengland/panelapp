from django.db import models
from autoslug import AutoSlugField


class PanelType(models.Model):
    name = models.CharField(max_length=128, unique=True)
    slug = AutoSlugField(populate_from='name', unique=True)
    description = models.TextField()

    def __str__(self):
        return self.name
