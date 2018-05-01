import csv
from datetime import datetime

from django.contrib import messages
from django.http import Http404
from django.shortcuts import get_list_or_404
from django.db.models import Q
from django.views.generic.base import View
from django.views.generic import FormView
from django.views.generic import ListView
from django.views.generic import UpdateView
from django.views.generic import DetailView
from django.views.generic import CreateView
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.functional import cached_property
from django.template.defaultfilters import pluralize
from django.http import HttpResponse
from django.http import StreamingHttpResponse

from panelapp.mixins import GELReviewerRequiredMixin
from panelapp.mixins import VerifiedReviewerRequiredMixin
from panels.forms import UploadGenesForm
from panels.forms import UploadPanelsForm
from panels.forms import UploadReviewsForm
from panels.forms import PanelForm
from panels.forms import PromotePanelForm
from panels.forms import PanelGeneForm
from panels.forms import GeneReadyForm
from panels.forms import GeneReviewForm
from panels.forms import ComparePanelsForm
from panels.forms import CopyReviewsForm
from panels.models import Tag
from panels.models import STR

from panels.models import GenePanel
from panels.models import GenePanelSnapshot
from panels.models import GenePanelEntrySnapshot
from panels.models import ProcessingRunCode
from panels.models import STR
from panels.mixins import PanelMixin
from panels.utils import remove_non_ascii
from .entities import EchoWriter


class DownloadPanelTSVMixin(PanelMixin, DetailView):
    model = GenePanelSnapshot

    def get(self, *args, **kwargs):
        return self.process()

    def process(self):
        self.object = self.get_object()

        panel_name = self.object.panel.name
        version = self.object.version

        response = HttpResponse(content_type='text/tab-separated-values')
        panel_name = remove_non_ascii(panel_name, replacemenet='_')
        response['Content-Disposition'] = 'attachment; filename="' + panel_name + '.tsv"'
        writer = csv.writer(response, delimiter='\t')

        writer.writerow((
            "Gene Entity Symbol",
            "Entity type",
            "Sources(; separated)",
            "Level4",
            "Level3",
            "Level2",
            "Model_Of_Inheritance",
            "Phenotypes",
            "Omim",
            "Orphanet",
            "HPO",
            "Publications",
            "Description",
            "Flagged",
            "GEL_Status",
            "UserRatings_Green_amber_red",
            "version",
            "ready",
            "Mode of pathogenicity",
            "EnsemblId(GRch37)",
            "EnsemblId(GRch38)",
            "HGNC",
            "STR Position Chromosome",
            "STR Position GRCh37 Start",
            "STR Position GRCh37 End",
            "STR Position GRCh38 Start",
            "STR Position GRCh38 End",
            "STR Repeated Sequence",
            "STR Normal Repeats",
            "STR Pathogenic Repeats",
        ))

        categories = self.get_categories()
        for gpentry in self.object.get_all_genes_extra:
            if not gpentry.flagged and str(gpentry.status) in categories:
                amber_perc, green_perc, red_prec = gpentry.aggregate_ratings()

                evidence = ";".join([evidence.name for evidence in gpentry.evidence.all()])
                export_gpentry = (
                    gpentry.gene.get('gene_symbol'),
                    'gene',
                    evidence,
                    panel_name,
                    self.object.level4title.level3title,
                    self.object.level4title.level2title,
                    gpentry.moi,
                    ";".join(map(remove_non_ascii, gpentry.phenotypes)),
                    ";".join(map(remove_non_ascii, self.object.level4title.omim)),
                    ";".join(map(remove_non_ascii, self.object.level4title.orphanet)),
                    ";".join(map(remove_non_ascii, self.object.level4title.hpo)),
                    ";".join(map(remove_non_ascii, gpentry.publications)),
                    "",
                    str(gpentry.flagged),
                    str(gpentry.saved_gel_status),
                    ";".join(map(str, [green_perc, amber_perc, red_prec])),
                    str(version),
                    gpentry.ready,
                    gpentry.mode_of_pathogenicity,
                    gpentry.gene.get('ensembl_genes', {}).get('GRch37', {}).get('82', {}).get('ensembl_id', '-'),
                    gpentry.gene.get('ensembl_genes', {}).get('GRch38', {}).get('90', {}).get('ensembl_id', '-'),
                    gpentry.gene.get('hgnc_id', '-'),
                    '-',
                    '-',
                    '-',
                    '-',
                    '-',
                    '-',
                    '-',
                    '-',
                    '-',
                )
                writer.writerow(export_gpentry)

        for strentry in self.object.get_all_strs_extra:
            if not strentry.flagged and str(strentry.status) in categories:
                amber_perc, green_perc, red_prec = strentry.aggregate_ratings()

                evidence = ";".join([evidence.name for evidence in strentry.evidence.all()])
                export_strentry = (
                    strentry.name,
                    'str',
                    evidence,
                    panel_name,
                    self.object.level4title.level3title,
                    self.object.level4title.level2title,
                    strentry.moi,
                    ";".join(map(remove_non_ascii, strentry.phenotypes)),
                    ";".join(map(remove_non_ascii, self.object.level4title.omim)),
                    ";".join(map(remove_non_ascii, self.object.level4title.orphanet)),
                    ";".join(map(remove_non_ascii, self.object.level4title.hpo)),
                    ";".join(map(remove_non_ascii, strentry.publications)),
                    "",
                    str(strentry.flagged),
                    str(strentry.saved_gel_status),
                    ";".join(map(str, [green_perc, amber_perc, red_prec])),
                    str(version),
                    strentry.ready,
                    '-',
                    strentry.gene.get('ensembl_genes', {}).get('GRch37', {}).get('82', {}).get('ensembl_id', '-') if strentry.gene else '',
                    strentry.gene.get('ensembl_genes', {}).get('GRch38', {}).get('90', {}).get('ensembl_id', '-') if strentry.gene else '',
                    strentry.gene.get('hgnc_id', '-') if strentry.gene else '',
                    strentry.chromosome,
                    strentry.position_37.lower,
                    strentry.position_37.upper,
                    strentry.position_38.lower,
                    strentry.position_38.upper,
                    strentry.repeated_sequence,
                    strentry.normal_repeats,
                    strentry.pathogenic_repeats,
                )
                writer.writerow(export_strentry)

        return response


class DownloadPanelTSVView(DownloadPanelTSVMixin):
    def get_categories(self):
        return self.kwargs['categories']


class DownloadPanelVersionTSVView(DownloadPanelTSVMixin):
    def get_categories(self):
        return '01234'

    def get_object(self):
        panel_version = self.request.POST.get('panel_version')
        if panel_version:
            return GenePanel.objects.get_panel(pk=self.kwargs['pk'])\
                .get_panel_version(panel_version)
        else:
            return GenePanel.objects.get_active_panel(pk=self.kwargs['pk'])

    def post(self, *args, **kwargs):
        self.object = self.get_object()
        if not self.object:
            msg = "Can't find panel with the version {}".format(self.request.POST.get('panel_version'))
            messages.error(self.request, msg)
            return redirect(reverse_lazy('panels:detail', kwargs={'pk': self.kwargs['pk']}))
        else:
            return self.process()


class ComparePanelsView(FormView):
    template_name = 'panels/compare/compare_panels.html'
    form_class = ComparePanelsForm

    def form_valid(self, form):
        panel_1 = form.cleaned_data['panel_1']
        panel_2 = form.cleaned_data['panel_2']
        return redirect(reverse_lazy('panels:compare', args=(panel_1.panel.pk, panel_2.panel.pk)))

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        is_admin = True if self.request.user.is_authenticated and self.request.user.reviewer.is_GEL() else False
        kwargs['panels'] = GenePanelSnapshot.objects.get_active(all=is_admin, internal=is_admin)

        return kwargs

    def get_context_data(self, *args, **kwargs):
        ctx = super().get_context_data()

        if self.kwargs.get('panel_1_id') and self.kwargs.get('panel_2_id'):
            ctx['panel_1'] = panel_1 = GenePanel.objects.get_panel(
                pk=self.kwargs['panel_1_id']).active_panel
            ctx['panel_2'] = panel_2 = GenePanel.objects.get_panel(
                pk=self.kwargs['panel_2_id']).active_panel

            panel_1_items = {e.gene.get('gene_symbol'): e for e in panel_1.get_all_genes_extra}
            panel_2_items = {e.gene.get('gene_symbol'): e for e in panel_2.get_all_genes_extra}

            all = list(set(panel_1_items.keys()) | set(panel_2_items.keys()))
            all.sort()

            intersection = list(set(panel_1_items.keys() & set(panel_2_items.keys())))
            ctx['show_copy_reviews'] = self.request.user.is_authenticated\
                and self.request.user.reviewer.is_GEL() and len(intersection) > 0

            comparison = [
                [
                    gene,
                    panel_1_items[gene] if gene in panel_1_items else False,
                    panel_2_items[gene] if gene in panel_2_items else False
                ] for gene in all
            ]

            ctx['comparison'] = comparison
        else:
            ctx['panel_1'] = None
            ctx['panel_2'] = None
            ctx['show_copy_reviews'] = None
            ctx['comparison'] = None

        return ctx


class CompareGeneView(FormView):
    template_name = 'panels/compare/compare_genes.html'
    form_class = ComparePanelsForm

    def form_valid(self, form):
        panel_1 = form.cleaned_data['panel_1']
        panel_2 = form.cleaned_data['panel_2']
        args = (panel_1.panel.pk, panel_2.panel.pk, self.kwargs['gene_symbol'])
        return redirect(reverse_lazy('panels:compare_genes', args=args))

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        is_admin = True if self.request.user.is_authenticated and self.request.user.reviewer.is_GEL() else False
        kwargs['panels'] = GenePanelSnapshot.objects.get_active(all=is_admin, internal=is_admin)

        return kwargs

    def get_context_data(self, *args, **kwargs):
        ctx = super().get_context_data()
        gene_symbol = self.kwargs['gene_symbol']
        ctx['gene_symbol'] = gene_symbol

        ctx['panel_1'] = panel_1 = GenePanel.objects.get_panel(
            pk=self.kwargs['panel_1_id']).active_panel
        ctx['panel_2'] = panel_2 = GenePanel.objects.get_panel(
            pk=self.kwargs['panel_2_id']).active_panel
        ctx['panel_1_entry'] = panel_1.get_gene(gene_symbol, prefetch_extra=True)
        ctx['panel_2_entry'] = panel_2.get_gene(gene_symbol, prefetch_extra=True)

        return ctx


class CopyReviewsView(GELReviewerRequiredMixin, FormView):
    template_name = 'panels/compare/copy_reviews.html'
    form_class = CopyReviewsForm

    def form_valid(self, form):
        ctx = self.get_context_data()
        process_type, total_count = form.copy_reviews(
            self.request.user.pk,
            ctx['intersection'],
            ctx['panel_1'],
            ctx['panel_2']
        )

        if process_type == ProcessingRunCode.PROCESSED:
            messages.success(self.request, "{} review{} copied".format(total_count, pluralize(total_count)))
        else:
            messages.error(self.request, "Panels have too many genes, reviews will be copied in the background.")

        return redirect(reverse_lazy('panels:compare', args=(ctx['panel_1'].panel.pk, ctx['panel_2'].panel.pk)))

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['initial'] = {
            'panel_1': GenePanel.objects.get_panel(
                pk=self.kwargs['panel_1_id']).active_panel.pk,
            'panel_2': GenePanel.objects.get_panel(
                pk=self.kwargs['panel_2_id']).active_panel.pk
        }
        return kwargs

    def form_invalid(self, form):
        return super().form_invalid(form)

    def get_context_data(self, *args, **kwargs):
        ctx = super().get_context_data(*args, **kwargs)

        ctx['panel_1'] = panel_1 = GenePanel.objects.get_panel(
            pk=self.kwargs['panel_1_id']).active_panel
        ctx['panel_2'] = panel_2 = GenePanel.objects.get_panel(
            pk=self.kwargs['panel_2_id']).active_panel

        panel_1_items = {e.gene.get('gene_symbol'): e for e in panel_1.get_all_genes_extra}
        panel_2_items = {e.gene.get('gene_symbol'): e for e in panel_2.get_all_genes_extra}

        intersection = list(set(panel_1_items.keys() & set(panel_2_items.keys())))
        intersection.sort()
        ctx['intersection'] = intersection

        comparison = [[gene, panel_1_items[gene], panel_2_items[gene]] for gene in intersection]
        ctx['comparison'] = comparison

        return ctx


class DownloadAllGenes(GELReviewerRequiredMixin, View):
    def gene_iterator(self):
        yield (
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
            "HGNC",
            "Biotype",
            "Phenotypes",
            "GeneLocation((GRch37)",
            "GeneLocation((GRch38)"
        )

        for gps in GenePanelSnapshot.objects.get_active(all=True, internal=True):
            for entry in gps.get_all_genes_extra:
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
                    entry.gene.get('gene_symbol'),
                    entry.panel.panel.pk,
                    entry.panel.level4title.name,
                    entry.panel.version,
                    str(entry.panel.panel.status).upper(),
                    colour,
                    ';'.join([evidence.name for evidence in entry.evidence.all()]),
                    entry.moi,
                    entry.mode_of_pathogenicity,
                    ';'.join([tag.name for tag in entry.tags.all()]),
                    entry.gene.get('ensembl_genes', {}).get('GRch37', {}).get('82', {}).get('ensembl_id', '-'),
                    entry.gene.get('ensembl_genes', {}).get('GRch38', {}).get('90', {}).get('ensembl_id', '-'),
                    entry.gene.get('hgnc_id', '-'),
                    entry.gene.get('biotype', '-'),
                    phenotypes,
                    entry.gene.get('ensembl_genes', {}).get('GRch37', {}).get('82', {}).get('location', '-'),
                    entry.gene.get('ensembl_genes', {}).get('GRch38', {}).get('90', {}).get('location', '-'),
                ]
                yield row

    def get(self, request, *args, **kwargs):
        pseudo_buffer = EchoWriter()
        writer = csv.writer(pseudo_buffer, delimiter='\t')

        response = StreamingHttpResponse((writer.writerow(row) for row in self.gene_iterator()),
                                         content_type='text/tab-separated-values')
        attachment = 'attachment; filename=All_genes_{}.tsv'.format(
            datetime.now().strftime('%Y%m%d-%H%M'))
        response['Content-Disposition'] = attachment
        return response