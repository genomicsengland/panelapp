from django.db import models

from django.contrib.postgres.fields import JSONField
from django.contrib.postgres.fields import ArrayField
from model_utils import Choices
from model_utils.models import TimeStampedModel

from accounts.models import User
from .genepanelsnapshot import GenePanelSnapshot
from .gene import Gene
from .evidence import Evidence
from .evaluation import Evaluation
from .trackrecord import TrackRecord
from .comment import Comment
from .tag import Tag


class GenePanelEntrySnapshotManager(models.Manager):
    pass


class GenePanelEntrySnapshot(TimeStampedModel):
    PENETRANCE = Choices(
        ("unknown", "unknown"),
        ("Complete", "Complete"),
        ("Incomplete", "Incomplete"),
    )

    GEL_STATUS = Choices(
        (0, "No list"),
        (1, "Red"),
        (2, "Amber"),
        (3, "Green"),
    )

    class Meta:
        get_latest_by = "created"
        ordering = ['-saved_gel_status', '-created', ]

    panel = models.ForeignKey(GenePanelSnapshot)
    gene = JSONField()  # copy data from Gene.dict_tr
    gene_core = models.ForeignKey(Gene)  # reference to the original Gene
    evidence = models.ManyToManyField(Evidence)
    evaluation = models.ManyToManyField(Evaluation)
    moi = models.CharField("Mode of inheritance", choices=Evaluation.MODES_OF_INHERITANCE, max_length=255)
    penetrance = models.CharField(choices=PENETRANCE, max_length=255)
    track = models.ManyToManyField(TrackRecord)
    publications = ArrayField(models.CharField(max_length=255))
    phenotypes = ArrayField(models.CharField(max_length=255))
    tags = models.ManyToManyField(Tag)
    flagged = models.BooleanField(default=False)
    ready = models.BooleanField(default=False)
    comments = models.ManyToManyField(Comment)
    contributors = models.ManyToManyField(User)
    mode_of_pathogenicity = models.CharField(choices=Evaluation.MODES_OF_PHATHOGENICITY, max_length=255)
    saved_gel_status = models.IntegerField(null=True)

    objects = GenePanelEntrySnapshotManager()

    def __str__(self):
        return "Panel: {} Gene: {}".format(self.panel.panel.name, self.gene.get('gene_symbol'))

    @property
    def status(self):
        """
        Save gel_status in the gene panel snapshot
        """

        if self.saved_gel_status is None:
            self.status = self.evidence_status()
            self.save()
        return self.saved_gel_status

    @status.setter
    def status(self, value):
        self.saved_gel_status = value

    @status.deleter
    def status(self):
        self.saved_gel_status = None

    def evidence_status(self, update=False):
        """
        This is a refactored `get_gel_status` function.
        It goes through evidences, check if they are valid or were provided by
        curators, and returns the status.
        This status is later used to determine the colour on the frontend and APIs
        """

        if self.flagged:
            return 0

        gel_status = 0
        for evidence in self.evidence.all():
            if evidence.is_GEL:
                if evidence.name in evidence.EXPERT_REVIEWS:
                    return evidence.EXPERT_REVIEWS.get(evidence.name)
                if evidence.name in evidence.HIGH_CONFIDENCE_SOURCES and evidence.rating > 3:
                    gel_status += 1

        if update:
            self.saved_gel_status = gel_status
            self.save()

        return gel_status

    def is_reviewd_by_user(self, user):
        return True if self.evaluation.filter(user=user).count() > 0 else False

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
            "tags": [tag.name for tag in self.tags.all()]
        }
