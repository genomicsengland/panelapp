"""Regions manager and model

Author: Oleg Gerasimenko

(c) 2018 Genomics England
"""

from django.db import models
from django.db.models import Subquery
from django.db.models import Count
from django.db.models import Value as V
from django.core.serializers.json import DjangoJSONEncoder
from django.contrib.postgres.fields import JSONField
from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.fields import IntegerRangeField
from django.core import validators
from django.urls import reverse

from model_utils.models import TimeStampedModel
from model_utils import Choices
from .entity import AbstractEntity
from .entity import EntityManager
from .gene import Gene
from .genepanel import GenePanel
from .evidence import Evidence
from .evaluation import Evaluation
from .trackrecord import TrackRecord
from .comment import Comment
from .tag import Tag
from .genepanelsnapshot import GenePanelSnapshot


class RegionManager(EntityManager):
    """Regions Objects manager."""

    def get_latest_ids(self, deleted=False):
        """Get Region ids"""

        qs = super().get_queryset()
        if not deleted:
            qs = qs.exclude(panel__panel__status=GenePanel.STATUS.deleted)

        return qs.distinct('panel__panel__pk')\
            .values_list('panel__pk', flat=True)\
            .order_by('panel__panel__pk', '-panel__major_version', '-panel__minor_version')

    def get_active(self, deleted=False, name=None, gene_symbol=None, pks=None, panel_types=None):
        """Get active Regions"""

        if pks:
            qs = super().get_queryset().filter(panel__pk__in=pks)
        else:
            qs = super().get_queryset().filter(panel__pk__in=Subquery(self.get_latest_ids(deleted)))
        if name:
            if isinstance(name, list):
                qs = qs.filter(name__in=name)
            else:
                qs = qs.filter(name=name)
        if gene_symbol:
            if isinstance(gene_symbol, list):
                qs = qs.filter(gene_core__gene_symbol__in=gene_symbol)
            else:
                qs = qs.filter(gene_core__gene_symbol=gene_symbol)

        if panel_types:
            qs = qs.filter(panel__panel__types__slug__in=panel_types)

        return qs.annotate(
                number_of_reviewers=Count('evaluation__user', distinct=True),
                number_of_evaluated_genes=Count('evaluation'),
                number_of_genes=Count('pk'),
                entity_type=V('region', output_field=models.CharField()),
                entity_name=models.F('name')
            )\
            .prefetch_related('evaluation', 'tags', 'evidence', 'panel', 'panel__level4title', 'panel__panel')\
            .order_by('panel__pk', '-panel__major_version', '-panel__minor_version')

    def get_region_panels(self, name, deleted=False, pks=None):
        """Get panels for the specified region name"""

        return self.get_active(deleted=deleted, name=name, pks=pks)


class Region(AbstractEntity, TimeStampedModel):
    """Regions Entity"""

    CHROMOSOMES = [
        ('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5'), ('6', '6'), ('7', '7'),
        ('8', '8'), ('9', '9'), ('10', '10'), ('11', '11'), ('12', '12'), ('13', '13'), ('14', '14'),
        ('15', '15'), ('16', '16'), ('17', '17'), ('18', '18'), ('19', '19'), ('20', '20'), ('21', '21'),
        ('22', '22'), ('X', 'X'), ('Y', 'Y')
    ]

    VARIANT_TYPES = Choices(
        ('small', 'Small variants'),
        ('cnv_loss', 'CNV Loss'),
        ('cnv_gain', 'CNV Gain'),
        ('cnv_both', 'CNV Both gain and loss'),
    )

    DOSAGE_SENSITIVITY_SCORES = (
        ('', ''),
        ('3', 'Sufficient evidence suggesting dosage sensitivity is associated with clinical phenotype'),
        ('2', 'Emerging evidence suggesting dosage sensitivity is associated with clinical phenotype'),
        ('1', 'Little evidence suggesting dosage sensitivity is associated with clinical phenotype'),
        ('0', 'No evidence to suggest that dosage sensitivity is associated with clinical phenotype'),
        ('40', 'Dosage sensitivity unlikely'),
        ('30', 'Gene associated with autosomal recessive phenotype')
    )

    class Meta:
        get_latest_by = "created"
        ordering = ['-saved_gel_status', ]
        indexes = [
            models.Index(fields=['name'])
        ]

    panel = models.ForeignKey(GenePanelSnapshot, on_delete=models.PROTECT)

    name = models.CharField(max_length=128, help_text="Region ID")
    verbose_name = models.CharField(max_length=256, blank=True, null=True, help_text='Region Name')
    chromosome = models.CharField(max_length=8, choices=CHROMOSOMES)
    position_37 = IntegerRangeField(blank=True, null=True)
    position_38 = IntegerRangeField()
    haploinsufficiency_score = models.CharField(max_length=2, choices=DOSAGE_SENSITIVITY_SCORES, blank=True, null=True)
    triplosensitivity_score = models.CharField(max_length=2, choices=DOSAGE_SENSITIVITY_SCORES, blank=True, null=True)
    required_overlap_percentage = models.IntegerField(help_text='Required percent of overlap',
                                                      validators=[validators.MinValueValidator(0),
                                                                  validators.MaxValueValidator(100)])
    type_of_variants = models.CharField("Variation type", max_length=32, choices=VARIANT_TYPES,
                                        default=VARIANT_TYPES.small)

    gene = JSONField(encoder=DjangoJSONEncoder, blank=True, null=True)  # copy data from Gene.dict_tr
    gene_core = models.ForeignKey(Gene, blank=True, null=True, on_delete=models.PROTECT)  # reference to the original Gene
    evidence = models.ManyToManyField(Evidence)
    evaluation = models.ManyToManyField(Evaluation, db_index=True)
    moi = models.CharField("Mode of inheritance", choices=Evaluation.MODES_OF_INHERITANCE, max_length=255)
    penetrance = models.CharField(choices=AbstractEntity.PENETRANCE, max_length=255, blank=True, null=True)
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

    objects = RegionManager()

    def __str__(self):
        return "Panel: {panel_name} Region: {region_name}".format(
            panel_name=self.panel.panel.name,
            region_name=self.name
        )

    @property
    def _entity_type(self):
        return 'region'

    @property
    def label(self):
        return 'Region: {name}'.format(name=self.name)

    def get_absolute_url(self):
        """Returns absolute url for this Region in a panel"""

        return reverse('panels:evaluation', args=(self.panel.panel.pk, 'region', self.name))

    def dict_tr(self):
        return {
            "name": self.name,
            "verbose_name": self.verbose_name,
            "chromosome": self.chromosome,
            "position_37": (self.position_37.lower, self.position_37.upper),
            "position_38": (self.position_38.lower, self.position_38.upper),
            "haploinsufficiency_score": self.haploinsufficiency_score,
            "triplosensitivity_score": self.triplosensitivity_score,
            "gene": self.gene,
            "evidence": [evidence.dict_tr() for evidence in self.evidence.all()],
            "evaluation": [evaluation.dict_tr() for evaluation in self.evaluation.all()],
            "track": [track.dict_tr() for track in self.track.all()],
            "moi": self.moi,
            "publications": self.publications,
            "phenotypes": self.phenotypes,
            "flagged": self.flagged,
            "penetrance": self.penetrance,
            "tags": [tag.name for tag in self.tags.all()]
        }

    @property
    def human_haploinsufficiency_score(self):
        if not self.haploinsufficiency_score:
            return ''

        for values in self.DOSAGE_SENSITIVITY_SCORES:
            if values[0] == self.haploinsufficiency_score:
                return values[1]
        else:
            return ''

    @property
    def human_triplosensitivity_score(self):
        if not self.triplosensitivity_score:
            return ''

        for values in self.DOSAGE_SENSITIVITY_SCORES:
            if values[0] == self.triplosensitivity_score:
                return values[1]
        else:
            return ''

    def get_form_initial(self):
        """Since we create a new version every time we want to update something this method
        gets the initial data for the form.
        """

        return {
            "name": self.name,
            "verbose_name": self.verbose_name,
            "chromosome": self.chromosome,
            "position_37": self.position_37,
            "position_38": self.position_38,
            "haploinsufficiency_score": self.haploinsufficiency_score,
            "triplosensitivity_score": self.triplosensitivity_score,
            "gene": self.gene_core,
            "gene_json": self.gene,
            "gene_name": self.gene.get('gene_name') if self.gene else None,
            "source": [e.name for e in self.evidence.all() if e.is_GEL],
            "tags": self.tags.all(),
            "publications": self.publications,
            "phenotypes": self.phenotypes,
            "moi": self.moi,
            "penetrance": self.penetrance
        }
