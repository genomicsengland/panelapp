"""STRs (Short Tandem Repeats) manager and model

Author: Oleg Gerasimenko

(c) 2018 Genomics England
"""

from django.db import models
from django.core.serializers.json import DjangoJSONEncoder
from django.contrib.postgres.fields import JSONField
from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.fields import IntegerRangeField
from django.urls import reverse

from model_utils.models import TimeStampedModel
from array_field_select.fields import ArrayField as SelectArrayField
from .entity import AbstractEntity
from .entity import EntityManager
from .gene import Gene
from .evidence import Evidence
from .evaluation import Evaluation
from .trackrecord import TrackRecord
from .comment import Comment
from .tag import Tag
from .genepanelsnapshot import GenePanelSnapshot


class RegionManager(EntityManager):
    """STR Objects manager."""

    def get_region_panels(self, name, deleted=False, pks=None):
        """Get panels for the specified region name"""

        return self.get_active(deleted=deleted, name=name, pks=pks)


class Region(AbstractEntity, TimeStampedModel):
    """Regions Entity"""

    CHROMOSOMES = [
        ('0', '0'),  ('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5'), ('6', '6'), ('7', '7'),
        ('8', '8'), ('9', '9'), ('10', '10'), ('11', '11'), ('12', '12'), ('13', '13'), ('14', '14'),
        ('15', '15'), ('16', '16'), ('17', '17'), ('18', '18'), ('19', '19'), ('20', '20'), ('21', '21'),
        ('22', '22'), ('X', 'X'), ('Y', 'Y')
    ]

    VARIANT_TYPES = [
        ('Small', 'Small'),
        ('SV', 'SV'),
        ('CNV', 'CNV'),
    ]

    EFFECT_TYPES = [
        ('transcript_ablation', 'A feature ablation whereby the deleted region includes a transcript feature'),
        ('splice_acceptor_variant', 'A splice variant that changes the 2 base region at the 3\' end of an intron'),
        ('splice_donor_variant', 'A splice variant that changes the 2 base region at the 5\' end of an intron'),
        ('stop_gained', 'A sequence variant whereby at least one base of a codon is changed, resulting in a premature stop codon, leading to a shortened transcript'),
        ('frameshift_variant', 'A sequence variant which causes a disruption of the translational reading frame, because the number of nucleotides inserted or deleted is not a multiple of three'),
        ('stop_lost', 'A sequence variant where at least one base of the terminator codon (stop) is changed, resulting in an elongated transcript'),
        ('start_lost', 'A codon variant that changes at least one base of the canonical start codon'),
        ('transcript_amplification', 'A feature amplification of a region containing a transcript'),
        ('inframe_insertion', 'An inframe non synonymous variant that inserts bases into in the coding sequence'),
        ('inframe_deletion', 'An inframe non synonymous variant that deletes bases from the coding sequence'),
        ('missense_variant', 'A sequence variant, that changes one or more bases, resulting in a different amino acid sequence but where the length is preserved'),
        ('protein_altering_variant', 'A sequence_variant which is predicted to change the protein encoded in the coding sequence'),
        ('splice_region_variant', 'A sequence variant in which a change has occurred within the region of the splice site, either within 1-3 bases of the exon or 3-8 bases of the intron'),
        ('incomplete_terminal_codon_variant', 'A sequence variant where at least one base of the final codon of an incompletely annotated transcript is changed'),
        ('start_retained_variant', 'A sequence variant where at least one base in the start codon is changed, but the start remains'),
        ('stop_retained_variant', 'A sequence variant where at least one base in the terminator codon is changed, but the terminator remains'),
        ('synonymous_variant', 'A sequence variant where there is no resulting change to the encoded amino acid'),
        ('coding_sequence_variant', 'A sequence variant that changes the coding sequence'),
        ('mature_miRNA_variant', 'A transcript variant located with the sequence of the mature miRNA'),
        ('5_prime_UTR_variant', 'A UTR variant of the 5\' UTR'),
        ('3_prime_UTR_variant', 'A UTR variant of the 3\' UTR'),
        ('non_coding_transcript_exon_variant', 'A sequence variant that changes non-coding exon sequence in a non-coding transcript'),
        ('intron_variant', 'A transcript variant occurring within an intron'),
        ('NMD_transcript_variant', 'A variant in a transcript that is the target of NMD'),
        ('non_coding_transcript_variant', 'A transcript variant of a non coding RNA gene'),
        ('upstream_gene_variant', 'A sequence variant located 5\' of a gene'),
        ('downstream_gene_variant', 'A sequence variant located 3\' of a gene'),
        ('TFBS_ablation', 'A feature ablation whereby the deleted region includes a transcription factor binding site'),
        ('TFBS_amplification', 'A feature amplification of a region containing a transcription factor binding site'),
        ('TF_binding_site_variant', 'A sequence variant located within a transcription factor binding site'),
        ('regulatory_region_ablation', 'A feature ablation whereby the deleted region includes a regulatory region'),
        ('regulatory_region_amplification', 'A feature amplification of a region containing a regulatory region'),
        ('feature_elongation', 'A sequence variant that causes the extension of a genomic feature, with regard to the reference sequence'),
        ('regulatory_region_variant', 'A sequence variant located within a regulatory region'),
        ('feature_truncation', 'A sequence variant that causes the reduction of a genomic feature, with regard to the reference sequence'),
        ('intergenic_variant', 'A sequence variant located in the intergenic region, between genes')
    ]

    class Meta:
        get_latest_by = "created"
        ordering = ['-saved_gel_status', ]
        indexes = [
            models.Index(fields=['panel_id']),
            models.Index(fields=['gene_core_id']),
            models.Index(fields=['name'])
        ]

    panel = models.ForeignKey(GenePanelSnapshot)

    name = models.CharField(max_length=128)
    chromosome = models.CharField(max_length=8, choices=CHROMOSOMES)
    position_37 = IntegerRangeField()
    position_38 = IntegerRangeField()
    type_of_variants = models.CharField(max_length=32, choices=VARIANT_TYPES)
    type_of_effects = SelectArrayField(models.CharField(max_length=128, choices=EFFECT_TYPES), help_text="Press CTRL or CMD button to select multiple effects")

    gene = JSONField(encoder=DjangoJSONEncoder, blank=True, null=True)  # copy data from Gene.dict_tr
    gene_core = models.ForeignKey(Gene, blank=True, null=True)  # reference to the original Gene
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
    def entity_type(self):
        return 'region'

    @property
    def label(self):
        return 'Region: {name}'.format(name=self.name)

    def get_absolute_url(self):
        """Returns absolute url for this STR in a panel"""

        return reverse('panels:evaluation', args=(self.panel.panel.pk, 'region', self.name))

    def human_type_of_effects(self):
        effects_map = {v[0]: v[1] for v in self.EFFECT_TYPES}
        return [effects_map[k] for k in self.type_of_effects]

    def dict_tr(self):
        return {
            "name": self.name,
            "chromosome": self.chromosome,
            "position_37": (self.position_37.lower, self.position_37.upper),
            "position_38": (self.position_38.lower, self.position_38.upper),
            "type_of_variants": self.type_of_variants,
            "type_of_effects": self.type_of_effects,
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

    def get_form_initial(self):
        """Since we create a new version every time we want to update something this method
        gets the initial data for the form.
        """

        return {
            "name": self.name,
            "chromosome": self.chromosome,
            "position_37": self.position_37,
            "position_38": self.position_38,
            "type_of_variants": self.type_of_variants,
            "type_of_effects": self.type_of_effects,
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
