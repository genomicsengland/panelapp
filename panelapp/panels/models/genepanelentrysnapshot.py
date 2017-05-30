from django.db import models
from django.db.models import Count
from django.db.models import Subquery
from django.db.models import Case
from django.db.models import When
from django.db.models import IntegerField
from django.contrib.postgres.fields import JSONField
from django.contrib.postgres.fields import ArrayField
from model_utils.models import TimeStampedModel

from accounts.models import User
from .genepanelsnapshot import GenePanelSnapshot
from .gene import Gene
from .evidence import Evidence
from .evaluation import Evaluation
from .trackrecord import TrackRecord
from .comment import Comment


class GenePanelEntrySnapshotManager(models.Manager):
    def get_latest_ids(self):
        return super().get_queryset()\
            .distinct('panel__pk')\
            .values('pk')\
            .order_by('panel__pk', '-created', '-panel__major_version', '-panel__minor_version')

    def get_gene_list(self):
        return super().get_queryset()\
            .prefetch_related('evaluation')\
            .filter(pk__in=Subquery(self.get_latest_ids()))\
            .annotate(
                number_of_green=Count(Case(When(
                    genepanelentrysnapshot__evaluation__rating=Evaluation.RATINGS.GREEN), output_field=IntegerField()
                )),
                number_of_red=Count(Case(When(
                    genepanelentrysnapshot__evaluation__rating=Evaluation.RATINGS.RED), output_field=IntegerField()
                )),
                number_of_amber=Count(Case(When(
                    genepanelentrysnapshot__evaluation__rating=Evaluation.RATINGS.AMBER), output_field=IntegerField()
                )),
            )\
            .order_by('gene__name')


class GenePanelEntrySnapshot(TimeStampedModel):
    """
    At what point we copy stuff from Evaluation to GenePanelEntrySnapshot and do we need to do it?
    """

    class Meta:
        get_latest_by = "created"
        ordering = ['-created', ]

    panel = models.ForeignKey(GenePanelSnapshot)
    gene = JSONField()  # copy data from Gene.dict_tr
    gene_core = models.ForeignKey(Gene)  # reference to the original Gene
    evidence = models.ManyToManyField(Evidence)
    evaluation = models.ManyToManyField(Evaluation)
    moi = models.CharField("Mode of inheritance", max_length=255)
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
    saved_gel_status = models.IntegerField(null=True)

    objects = GenePanelEntrySnapshotManager()

    @property
    def status(self):
        """
        Save gel_status in the gene panel snapshot
        """

        if not self.saved_gel_status:
            self.saved_gel_status = self.evidence_status()
        return self.saved_gel_status

    @status.setter
    def status(self, value):
        self.saved_gel_status = value

    @status.deleter
    def status(self):
        self.saved_gel_status = None

    def evidence_status(self):
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
            "tags": self.tags
        }
