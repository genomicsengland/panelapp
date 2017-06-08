from django.db import models
from django.db.models import Count
from django.db.models import Subquery

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
    def get_latest_ids(self):
        return super().get_queryset()\
            .distinct('panel__panel')\
            .values_list('pk', flat=True)\
            .order_by('panel__panel', '-panel__major_version', '-panel__minor_version')

    def get_active(self):
        return super().get_queryset()\
            .filter(pk__in=Subquery(self.get_latest_ids()))\
            .annotate(
                number_of_reviewers=Count('evaluation__user', distinct=True),
                number_of_evaluated_genes=Count('evaluation'),
                number_of_genes=Count('pk'),
            )\
            .order_by('panel', '-panel__major_version', '-panel__minor_version')

    def get_gene_panels(self, gene_symbol):
        return self.get_active().filter(gene__gene_symbol=gene_symbol)


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

    def clear_evidences(self, user, evidence=None):
        self.panel.increment_version()

        if evidence:
            evidences = self.evidence.filter(name=evidence)
            if len(evidences) > 0:
                evidences.delete()

                description = "{} Source: {} was removed from gene: {}".format(
                    self.gene_core.gene_symbol,
                    evidence,
                    self.gene_core.gene_symbol
                )
            else:
                return False
        else:
            self.evidence.all().delete()

            description = "{} All sources for gene: {} were removed".format(
                self.gene_core.gene_symbol,
                self.gene_core.gene_symbol
            )
        evidence_status = self.evidence_status(update=True)
        track_sources = TrackRecord.objects.create(
            gel_status=evidence_status,
            curator_status=0,
            user=user,
            issue_type=TrackRecord.ISSUE_TYPES.ClearSources,
            issue_description=description
        )
        self.track.add(track_sources)

        return True

    def clear_expert_evidence(self, evidence):
        evidences = self.evidence.filter(name=evidence)
        if len(evidences) > 0:
            evidences.delete()
            return True
        else:
            return False

    def mark_as_ready(self, user, ready_comment):
        self.ready = True

        if ready_comment:
            comment = Comment.objects.create(
                user=user,
                comment="Comment when marking as ready: {}".format(ready_comment)
            )
            self.comments.add(comment)

        self.panel.add_activity(
            user,
            self.gene.get('gene_symbol'),
            "marked {} as ready".format(self.gene.get('gene_symbol'))
        )

        status = self.status
        [self.clear_expert_evidence(e) for e in Evidence.EXPERT_REVIEWS]

        if status > 3:
            evidence = Evidence.objects.create(name="Expert Review Green", rating=5, reviewer=user.reviewer)
            issue_description = "This gene has been classified as Green List (High Evidence)."
            self.flagged = False
            self.evidence.add(evidence)
        elif status > 1:
            evidence = Evidence.objects.create(name="Expert Review Amber", rating=5, reviewer=user.reviewer)
            issue_description = "This gene has been classified as Amber List (Moderate Evidence)."
            self.flagged = False
            self.evidence.add(evidence)
        elif status == 1:
            evidence = Evidence.objects.create(name="Expert Review Red", rating=5, reviewer=user.reviewer)
            issue_description = "This gene has been classified as Red List (Low Evidence)."
            self.evidence.add(evidence)
            self.flagged = False
        elif status == 0:
            evidence = Evidence.objects.create(name="Expert Review Removed", rating=5, reviewer=user.reviewer)
            issue_description="This gene has been removed from the panel."
            self.evidence.add(evidence)
            self.flagged = True
        else:
            return

        track = TrackRecord.objects.create(
            gel_status=status,
            curator_status=0,
            user=user,
            issue_type="Gene classified by Genomics England curator", issue_description=issue_description
        )
        self.track.add(track)
        self.save()

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

    def get_form_initial(self):
        return {
            "gene": self.gene_core,
            "gene_name": self.gene.get('gene_name'),
            "source": [e.name for e in self.evidence.all()],
            "tags": self.tags.all(),
            "publications": self.publications,
            "phenotypes": self.phenotypes,
            "mode_of_pathogenicity": self.mode_of_pathogenicity,
            "moi": self.moi,
            "penetrance": self.penetrance
        }
