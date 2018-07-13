from django.db import models
from model_utils import Choices
from django.urls import reverse

from django.core.serializers.json import DjangoJSONEncoder
from django.contrib.postgres.fields import JSONField
from django.contrib.postgres.fields import ArrayField

from model_utils.models import TimeStampedModel

from .gene import Gene
from .evidence import Evidence
from .evaluation import Evaluation
from .trackrecord import TrackRecord
from .comment import Comment
from .tag import Tag
from .genepanelsnapshot import GenePanelSnapshot
from .entity import AbstractEntity
from .entity import EntityManager


class GenePanelEntrySnapshotManager(EntityManager):
    """Objects manager for GenePanelEntrySnapshot."""

    pass


class GenePanelEntrySnapshot(AbstractEntity, TimeStampedModel):
    VARIANT_TYPES = Choices(
        ('small', 'Small variants'),
        ('cnv_loss', 'CNV_LOSS'),
        ('cnv_gain', 'CNV_GAIN')
    )

    class Meta:
        get_latest_by = "created"
        ordering = ['-saved_gel_status', ]
        indexes = [
            models.Index(fields=['panel_id']),
            models.Index(fields=['gene_core_id']),
            models.Index(fields=['ready']),
            models.Index(fields=['saved_gel_status']),
        ]

    panel = models.ForeignKey(GenePanelSnapshot, on_delete=models.PROTECT)
    gene = JSONField(encoder=DjangoJSONEncoder)  # copy data from Gene.dict_tr
    gene_core = models.ForeignKey(Gene, on_delete=models.PROTECT)  # reference to the original Gene
    evidence = models.ManyToManyField(Evidence)
    evaluation = models.ManyToManyField(Evaluation, db_index=True)
    moi = models.CharField("Mode of inheritance", choices=Evaluation.MODES_OF_INHERITANCE, max_length=255)
    penetrance = models.CharField(choices=AbstractEntity.PENETRANCE, max_length=255, blank=True, null=True)
    type_of_variants = models.CharField(max_length=32, choices=VARIANT_TYPES, default=VARIANT_TYPES.small)
    track = models.ManyToManyField(TrackRecord)
    publications = ArrayField(models.TextField(), blank=True, null=True)
    phenotypes = ArrayField(models.TextField(), blank=True, null=True)
    tags = models.ManyToManyField(Tag)
    flagged = models.BooleanField(default=False)
    ready = models.BooleanField(default=False)
    comments = models.ManyToManyField(Comment)
    mode_of_pathogenicity = models.CharField(
        choices=Evaluation.MODES_OF_PATHOGENICITY,
        max_length=255,
        null=True,
        blank=True
    )
    saved_gel_status = models.IntegerField(null=True, db_index=True)

    objects = GenePanelEntrySnapshotManager()

    def __str__(self):
        return "Panel: {} Gene: {}".format(self.panel.panel.name, self.gene.get('gene_symbol'))

    @property
    def _entity_type(self):
        return 'gene'

    @property
    def label(self):
        return 'gene: {gene_symbol}'.format(gene_symbol=self.gene.get('gene_symbol'))

    @property
    def name(self):
        return self.gene.get('gene_symbol')

    def get_absolute_url(self):
        """Returns absolute url for this gene in a panel"""

        return reverse('panels:evaluation', args=(self.panel.panel.pk, 'gene', self.gene.get('gene_symbol')))

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
        """Since we create a new version every time we want to update something this method
        gets the initial data for the form.
        """

        return {
            "gene": self.gene_core,
            "gene_json": self.gene,
            "gene_name": self.gene.get('gene_name'),
            "source": [e.name for e in self.evidence.all() if e.is_GEL],
            "tags": self.tags.all(),
            "publications": self.publications,
            "phenotypes": self.phenotypes,
            "mode_of_pathogenicity": self.mode_of_pathogenicity,
            "moi": self.moi,
            "penetrance": self.penetrance
        }
