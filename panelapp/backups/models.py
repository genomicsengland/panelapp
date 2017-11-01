import csv
from io import StringIO

from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.fields import JSONField
from django.core.files.base import File

from model_utils.models import TimeStampedModel
from slugify import slugify

from webservices.utils import make_null
from webservices.utils import convert_moi
from webservices.utils import convert_gel_status


class PanelBackup(TimeStampedModel):
    """Panels backups

    We store backups for every version of any panel. These backups are used
    when someone retrieves the information via webservices API or via
    TSV file download on the frontend.

    `content` is a JSON field that contains information we need for the API
    (so we minimise the conversion), plus some additional information for
    each gene like number of reviews, sources, etc, this information is
    stored in `__gel_internal` attribute of each gene.
    """

    class Meta:
        ordering = ['-major_version', '-minor_version']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['old_pk']),
            models.Index(fields=['original_pk']),
            models.Index(fields=['major_version']),
            models.Index(fields=['minor_version']),
        ]

    name = models.CharField(max_length=256)  # title - charfield
    old_panels = ArrayField(models.CharField(max_length=255), blank=True, null=True)
    old_pk = models.CharField(max_length=32, null=True)  # pa1 ids
    original_pk = models.IntegerField()  # pa2 ids
    major_version = models.IntegerField()
    minor_version = models.IntegerField()
    number_of_genes = models.IntegerField()
    gene_symbols = ArrayField(models.CharField(max_length=255), blank=True, null=True)
    genes_content = JSONField()

    def import_panel(self, gps):
        """Import GenePanelSnapshot

        Once something has been changed in GenePanelSnapshot it should create a
        new version. This should be called from `increment_version` method.

        But it can be generated in the background via Celery task.
        """

        self.name = gps.panel.name
        self.old_panels = gps.old_panels
        self.old_pk = gps.panel.old_pk
        self.original_pk = gps.panel.pk
        self.number_of_genes = gps.number_of_genes
        self.major_version = gps.major_version
        self.minor_version = gps.minor_version
        self.gene_symbols = gps.current_genes

        result = {
            "result": {
                "Genes": [],
                "SpecificDiseaseName": gps.panel.name,
                "version": gps.version,
                "DiseaseGroup": gps.level4title.level2title,
                "DiseaseSubGroup": gps.level4title.level3title,
                "__gel__internal": {
                    'omim': gps.level4title.omim,
                    'hpo': gps.level4title.hpo,
                    'orphanet': gps.level4title.orphanet
                }
            }
        }

        for gene in gps.get_all_entries:
            result['result']['Genes'].append({
                "GeneSymbol": gene.gene.get('gene_symbol'),
                "ModeOfInheritance": make_null(convert_moi(gene.moi)),
                "Penetrance": make_null(gene.penetrance),
                "Publications": make_null(gene.publications),
                "Phenotypes": make_null(gene.phenotypes),
                "ModeOfPathogenicity": make_null(gene.mode_of_pathogenicity),
                "LevelOfConfidence": convert_gel_status(gene.saved_gel_status),
                "Evidences": [ev.name for ev in gene.evidence.all()],
                "__gel_internal": {
                    'gene_data': gene.gene,
                    'ratings': list(gene.aggregate_ratings()),
                    'flagged': gene.flagged,
                    'ready': gene.ready
                }
            })

        self.genes_content = result
        self.save()

        self.create_tsv_file(gps)

    def create_tsv_file(self, gps):
        backup = TSVBackup()
        backup.panel_backup = self

        output = StringIO()
        writer = csv.writer(output, delimiter='\t')
        writer.writerow(gps.tsv_file_header())

        for gpentry in gps.tsv_file_export():
            writer.writerow(gpentry)

        backup.tsv.save(slugify(self.name), File(output))


def panel_version_path(instance, filename):
    """Returns a path for TSV backup"""

    return 'tsv_panels/{}/{}-{}.{}.tsv'.format(
        instance.panel_backup.original_pk,
        slugify(instance.panel_backup.name),
        instance.panel_backup.major_version,
        instance.panel_backup.minor_version
    )


class TSVBackup(TimeStampedModel):
    """Saved TSV exports which are available to download via the frontend
    """

    panel_backup = models.ForeignKey(PanelBackup)
    tsv = models.FileField(upload_to=panel_version_path)
