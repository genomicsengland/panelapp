from django.db import models
from django.contrib.postgres.fields import JSONField


class Gene(models.Model):
    gene_symbol = models.CharField(max_length=255, primary_key=True)
    gene_name = models.CharField(max_length=255)
    other_transcripts = JSONField()
    omim_gene = models.CharField(max_length=255)

    def __str__(self):
        return self.gene_symbol + ", " + self.gene_name

    def dict_tr(self):
        return {
            "gene_symbol": self.gene_symbol,
            "gene_name": self.gene_name,
            "other_transcripts": [t.dict_tr() for t in self.other_transcripts],
            "omim_gene": self.omim_gene,
        }
