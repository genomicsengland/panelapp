from django.db import models


class Variant(models.Model):
    chromosome = models.CharField(max_length=255)
    transcript = models.CharField(max_length=255)
    protein = models.CharField(max_length=255)
    change = models.CharField(max_length=255)
    consequence = models.CharField(max_length=255)
    pathogenicity = models.CharField(max_length=255)
    alternate = models.CharField(max_length=2500)
    reference = models.CharField(max_length=2500)
    position = models.IntegerField()

    def dict_tr(self):
        return {
            "chromosome": self.chromosome,
            "transcript": self.transcript,
            "protein": self.protein,
            "change": self.change,
            "consequence": self.consequence,
            "alternate": self.alternate,
            "reference": self.reference,
            "position": self.position
        }
