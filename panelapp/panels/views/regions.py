import csv
from datetime import datetime
from django.http import StreamingHttpResponse
from django.views import View
from panels.models import GenePanelSnapshot
from .entities import EchoWriter
from panelapp.mixins import GELReviewerRequiredMixin


class DownloadAllRegions(GELReviewerRequiredMixin, View):
    def regions_iterator(self):
        yield (
            "Name",
            "Verbose Name",
            "Chromosome",
            "Position GRCh37 start",
            "Position GRCh37 end",
            "Position GRCh38 start",
            "Position GRCh38 end",
            "Haploinsufficiency Score",
            "Triplosensitivity Score",
            "Required region overlap",
            "Variant types",
            "Symbol",
            "Panel Id",
            "Panel Name",
            "Panel Version",
            "Panel Status",
            "List",
            "Sources",
            "Mode of inheritance",
            "Tags",
            "EnsemblId(GRch37)",
            "EnsemblId(GRch38)",
            "Biotype",
            "Phenotypes",
            "GeneLocation(GRch37)",
            "GeneLocation(GRch38)"
        )

        for gps in GenePanelSnapshot.objects.get_active(all=True, internal=True).iterator():
            for entry in gps.get_all_regions_extra.prefetch_related('evidence'):
                color = entry.entity_color_name

                if isinstance(entry.phenotypes, list):
                    phenotypes = ';'.join(entry.phenotypes)
                else:
                    phenotypes = ''

                row = [
                    entry.name,
                    entry.verbose_name,
                    entry.chromosome,
                    entry.position_37.lower if entry.position_37 else '',
                    entry.position_37.upper if entry.position_37 else '',
                    entry.position_38.lower,
                    entry.position_38.upper,
                    entry.haploinsufficiency_score if entry.haploinsufficiency_score else '',
                    entry.triplosensitivity_score if entry.triplosensitivity_score else '',
                    entry.required_overlap_percentage,
                    entry.type_of_variants,
                    entry.gene.get('gene_symbol') if entry.gene else '',
                    gps.panel.pk,
                    gps.level4title.name,
                    gps.version,
                    str(gps.panel.status).upper(),
                    color,
                    ';'.join([evidence.name for evidence in entry.evidence.all()]),
                    entry.moi,
                    ';'.join([tag.name for tag in entry.tags.all()]),
                    entry.gene.get('ensembl_genes', {}).get('GRch37', {}).get('82', {}).get('ensembl_id', '') if entry.gene else '',
                    entry.gene.get('ensembl_genes', {}).get('GRch38', {}).get('90', {}).get('ensembl_id', '') if entry.gene else '',
                    entry.gene.get('biotype', '-') if entry.gene else '-',
                    phenotypes,
                    entry.gene.get('ensembl_genes', {}).get('GRch37', {}).get('82', {}).get('location', '') if entry.gene else '',
                    entry.gene.get('ensembl_genes', {}).get('GRch38', {}).get('90', {}).get('location', '') if entry.gene else '',
                ]
                yield row

    def get(self, request, *args, **kwargs):
        pseudo_buffer = EchoWriter()
        writer = csv.writer(pseudo_buffer, delimiter='\t')

        response = StreamingHttpResponse((writer.writerow(row) for row in self.regions_iterator()),
                                         content_type='text/tab-separated-values')
        attachment = 'attachment; filename=All_regions_{}.tsv'.format(
            datetime.now().strftime('%Y%m%d-%H%M'))
        response['Content-Disposition'] = attachment
        return response
