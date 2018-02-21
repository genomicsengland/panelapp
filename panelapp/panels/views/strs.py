import csv
from datetime import datetime
from django.http import StreamingHttpResponse
from django.views import View
from panels.models import GenePanelSnapshot
from .entities import EchoWriter
from panelapp.mixins import GELReviewerRequiredMixin


class DownloadAllSTRs(GELReviewerRequiredMixin, View):
    def gene_iterator(self):
        yield (
            "Name",
            "Position",
            "Normal range lower",
            "Normal range upper",
            "Pre-pathogenic range lower",
            "Pre-pathogenic range upper",
            "Pathogenic range lower",
            "Pathogenic range upper",
            "Symbol",
            "Panel Id",
            "Panel Name",
            "Panel Version",
            "Panel Status",
            "List",
            "Sources",
            "Mode of inheritance",
            "Mode of pathogenicity",
            "Tags",
            "EnsemblId(GRch37)",
            "EnsemblId(GRch38)",
            "Biotype",
            "Phenotypes",
            "GeneLocation((GRch37)",
            "GeneLocation((GRch38)"
        )

        for gps in GenePanelSnapshot.objects.get_active(all=True, internal=True):
            for entry in gps.get_all_strs_extra:
                if entry.flagged:
                    colour = "grey"
                elif entry.status < 2:
                    colour = "red"
                elif entry.status == 2:
                    colour = "amber"
                else:
                    colour = "green"

                if isinstance(entry.phenotypes, list):
                    phenotypes = ';'.join(entry.phenotypes)
                else:
                    phenotypes = '-'

                row = [
                    entry.name,
                    entry.position,
                    entry.normal_range.lower if entry.normal_range else '-',
                    entry.normal_range.upper if entry.normal_range else '-',
                    entry.prepathogenic_range.lower,
                    entry.prepathogenic_range.upper,
                    entry.pathogenic_range.lower,
                    entry.pathogenic_range.upper,
                    entry.gene.get('gene_symbol') if entry.gene else '-',
                    entry.panel.panel.pk,
                    entry.panel.level4title.name,
                    entry.panel.version,
                    str(entry.panel.panel.status).upper(),
                    colour,
                    ';'.join([evidence.name for evidence in entry.evidence.all()]),
                    entry.moi,
                    entry.mode_of_pathogenicity,
                    ';'.join([tag.name for tag in entry.tags.all()]),
                    entry.gene.get('ensembl_genes', {}).get('GRch37', {}).get('82', {}).get('ensembl_id', '-') if entry.gene else '-',
                    entry.gene.get('ensembl_genes', {}).get('GRch38', {}).get('90', {}).get('ensembl_id', '-') if entry.gene else '-',
                    entry.gene.get('biotype', '-') if entry.gene else '-',
                    phenotypes,
                    entry.gene.get('ensembl_genes', {}).get('GRch37', {}).get('82', {}).get('location', '-') if entry.gene else '-',
                    entry.gene.get('ensembl_genes', {}).get('GRch38', {}).get('90', {}).get('location', '-') if entry.gene else '-',
                ]
                yield row

    def get(self, request, *args, **kwargs):
        pseudo_buffer = EchoWriter()
        writer = csv.writer(pseudo_buffer, delimiter='\t')

        response = StreamingHttpResponse((writer.writerow(row) for row in self.gene_iterator()),
                                         content_type='text/tab-separated-values')
        attachment = 'attachment; filename=All_strs_{}.tsv'.format(
            datetime.now().strftime('%Y%m%d-%H%M'))
        response['Content-Disposition'] = attachment
        return response
