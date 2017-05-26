from django.db import models
from django.contrib.postgres.fields import JSONField
from django.contrib.postgres.fields import ArrayField

from accounts.models import User
from .genepanelsnapshot import GenePanelSnapshot
from .gene import Gene
from .evidence import Evidence
from .evaluation import Evaluation
from .trackrecord import TrackRecord
from .comment import Comment


# with GenePanelEntry - can you remove a single source, or you only able to remove all of them at once?
class GenePanelEntrySnapshot(models.Model):
    panel = models.ForeignKey(GenePanelSnapshot)
    gene = JSONField() # copy data from Gene.dict_tr
    gene_core = models.ForeignKey(Gene)  # reference to the original Gene
    evidence = models.ManyToManyField(Evidence)
    evaluation = models.ManyToManyField(Evaluation)
    moi = models.CharField(max_length=255)
    penetrance = models.CharField(max_length=255)
    track = models.ManyToManyField(TrackRecord)
    publications = ArrayField(models.CharField(max_length=255))
    phenotypes = ArrayField(models.CharField(max_length=255))
    tags = ArrayField(models.CharField(max_length=30))
    flagged = models.BooleanField(default=False)
    ready = models.BooleanField(default=False)
    comments = models.ManyToManyField(Comment)
    contributors = models.ManyToManyField(User)
    mode_of_pathogenicity = models.CharField(max_length=255)

    def dict_tr(self):
        return {
            "gene": self.gene,
            "evidence": [evidence.dict_tr() for evidence in self.evidence.all()],
            "evaluation": [evaluation.dict_tr() for evaluation in self.evaluation.all()],
            "track": [track.dict_tr() for track in self.track.all()],
            "moi": self.moi,
            "publications": self.publications,
            "phenotypes": self.phenotypes,
            "flagged": self.flagged,
            "mode_of_pathogenicity": self.mode_of_pathogenicity,
            "penetrance": self.penetrance,
            "tags": self.tags
        }
