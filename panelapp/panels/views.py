import csv
from datetime import datetime
from django.contrib import messages
from django.db.models import Q
from django.views.generic import TemplateView
from django.views.generic.base import View
from django.views.generic import FormView
from django.views.generic import ListView
from django.views.generic import UpdateView
from django.views.generic import DetailView
from django.views.generic import CreateView
from django.shortcuts import redirect
from django.urls import reverse
from django.urls import reverse_lazy
from django.utils.functional import cached_property
from django.template.defaultfilters import pluralize
from django.http import HttpResponse

from panelapp.mixins import GELReviewerRequiredMixin
from panelapp.mixins import VerifiedReviewerRequiredMixin
from accounts.models import User
from .forms import UploadGenesForm
from .forms import UploadPanelsForm
from .forms import UploadReviewsForm
from .forms import PanelForm
from .forms import PromotePanelForm
from .forms import PanelGeneForm
from .forms import GeneReviewForm
from .forms import GeneReadyForm
from .forms import ComparePanelsForm
from .forms import CopyReviewsForm
from .forms.ajax import UpdateGeneTagsForm
from .forms.ajax import UpdateGeneMOPForm
from .forms.ajax import UpdateGeneMOIForm
from .forms.ajax import UpdateGenePhenotypesForm
from .forms.ajax import UpdateGenePublicationsForm
from .forms.ajax import UpdateGeneRatingForm
from .models import Tag
from .models import Gene
from .models import Activity
from .models import GenePanel
from .models import GenePanelSnapshot
from .models import GenePanelEntrySnapshot
from .mixins import PanelMixin
from .mixins import ActAndRedirectMixin
from .utils import remove_non_ascii


class PanelsIndexView(ListView):
    template_name = "panels/genepanel_list.html"
    model = GenePanelSnapshot
    context_object_name = 'panels'
    objects = []

    def get_queryset(self, *args, **kwargs):
        if self.request.GET.get('gene'):
            self.objects = GenePanelSnapshot.objects.get_gene_panels(self.request.GET.get('gene'))
        else:
            if self.request.user.is_authenticated and self.request.user.reviewer.is_GEL():
                self.objects = GenePanelSnapshot.objects.get_active_anotated(all=True)
            else:
                self.objects = GenePanelSnapshot.objects.get_active_anotated()
        return self.panels

    @cached_property
    def panels(self):
        return self.objects

    @cached_property
    def compare_panels_form(self):
        return ComparePanelsForm()

    def get_context_data(self, *args, **kwargs):
        ctx = super().get_context_data(*args, **kwargs)
        return ctx


class CreatePanelView(GELReviewerRequiredMixin, CreateView):
    template_name = "panels/genepanel_create.html"
    form_class = PanelForm

    def form_valid(self, form):
        self.instance = form.instance
        ret = super().form_valid(form)
        messages.success(self.request, "Successfully added a new panel")
        return ret

    def get_success_url(self):
        return reverse_lazy('panels:detail', kwargs={'pk': self.instance.panel.pk})


class UpdatePanelView(GELReviewerRequiredMixin, PanelMixin, UpdateView):
    template_name = "panels/genepanel_create.html"
    form_class = PanelForm

    def form_valid(self, form):
        self.instance = form.instance
        ret = super().form_valid(form)
        messages.success(self.request, "Successfully updated the panel")
        return ret


class GenePanelView(DetailView):
    model = GenePanel

    def get_context_data(self, *args, **kwargs):
        ctx = super().get_context_data(*args, **kwargs)
        ctx['panel'] = self.object.active_panel
        ctx['edit'] = PanelForm(initial=ctx['panel'].get_form_initial())
        ctx['contributors'] = User.objects.panel_contributors(ctx['panel'].pk)
        ctx['promote_panel_form'] = PromotePanelForm(
            instance=ctx['panel'],
            request=self.request,
            initial={'version_comment': None}
        )
        return ctx


class AdminContextMixin:
    def get_context_data(self, *args, **kwargs):
        ctx = super().get_context_data(*args, **kwargs)
        ctx['gene_form'] = UploadGenesForm()
        ctx['panel_form'] = UploadPanelsForm()
        ctx['review_form'] = UploadReviewsForm()
        return ctx


class AdminView(GELReviewerRequiredMixin, AdminContextMixin, TemplateView):
    template_name = "panels/admin.html"


class ImportToolMixin(GELReviewerRequiredMixin, AdminContextMixin, FormView):
    template_name = "panels/admin.html"
    success_url = reverse_lazy('panels:admin')

    def form_valid(self, form):
        ret = super().form_valid(form)
        form.process_file(user=self.request.user)
        messages.success(self.request, "Import successful")
        return ret


class AdminUploadGenesView(ImportToolMixin, AdminContextMixin):
    form_class = UploadGenesForm

    def get(self, request, *args, **kwargs):
        return redirect(reverse_lazy('panels:admin'))


class AdminUploadPanelsView(ImportToolMixin, AdminContextMixin):
    form_class = UploadPanelsForm

    def get(self, request, *args, **kwargs):
        return redirect(reverse_lazy('panels:admin'))


class AdminUploadReviewsView(ImportToolMixin, AdminContextMixin):
    form_class = UploadReviewsForm

    def get(self, request, *args, **kwargs):
        return redirect(reverse_lazy('panels:admin'))


class GeneDetailView(DetailView):
    model = Gene
    slug_field = 'gene_symbol'
    slug_field_kwarg = 'gene_symbol'
    context_object_name = 'gene'

    def get_context_data(self, *args, **kwargs):
        ctx = super().get_context_data(*args, **kwargs)
        tag_filter = self.request.GET.get('tag_filter', None)
        ctx['tag_filter'] = tag_filter
        ctx['gene_symbol'] = self.kwargs['slug']

        entries = GenePanelEntrySnapshot.objects.get_gene_panels(self.kwargs['slug'])
        if not self.request.user.is_authenticated or not self.request.user.reviewer.is_GEL():
            entries = entries.filter(panel__panel__approved=True)

        if tag_filter:
            entries = entries.filter(tag__name=tag_filter)

        ctx['entries'] = entries
        return ctx


class GeneListView(ListView):
    model = Gene
    context_object_name = "genes"
    template_name = "panels/gene_list.html"

    def get_queryset(self, *args, **kwargs):
        if self.request.user.is_authenticated and self.request.user.reviewer.is_GEL:
            panel_ids = GenePanelSnapshot.objects.get_latest_ids().values('pk')
        else:
            panel_ids = GenePanelSnapshot.objects.get_latest_ids().filter(panel__approved=True).values('pk')

        genes = GenePanelEntrySnapshot.objects.filter(
            gene_core__active=True,
            panel__in=panel_ids
        ).order_by().distinct('gene_core__gene_symbol').values_list('gene_core__gene_symbol', flat=True)

        return genes

    def get_context_data(self, *args, **kwargs):
        ctx = super().get_context_data(*args, **kwargs)
        ctx['tags'] = Tag.objects.all()
        ctx['tag_filter'] = self.request.GET.get('tag')
        return ctx


class PromotePanelView(GELReviewerRequiredMixin, GenePanelView, UpdateView):
    template_name = "panels/genepanel_detail.html"
    form_class = PromotePanelForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        kwargs['instance'] = self.object.active_panel
        return kwargs

    def form_valid(self, form):
        ret = super().form_valid(form)
        self.instance = form.instance.panel
        messages.success(self.request, "Successfully upgraded Panel {}".format(self.get_object().name))
        return ret

    def get_success_url(self):
        return reverse_lazy('panels:detail', args=(self.kwargs['pk'],))


class PanelAddGeneView(VerifiedReviewerRequiredMixin, CreateView):
    template_name = "panels/genepanel_add_gene.html"

    form_class = PanelGeneForm
    gene_symbol = None

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['panel'] = GenePanel.objects.get_active_panel(pk=self.kwargs['pk'])
        kwargs['request'] = self.request
        return kwargs

    def get_context_data(self, *args, **kwargs):
        ctx = super().get_context_data(*args, **kwargs)
        ctx['panel'] = self.panel
        return ctx

    @property
    def panel(self):
        return GenePanel.objects.get_active_panel(pk=self.kwargs['pk'])

    def form_valid(self, form):
        form.save_gene()
        self.gene_symbol = form.cleaned_data['gene'].gene_symbol

        ret = super().form_valid(form)
        msg = "Successfully added a new gene to the panel {}".format(self.panel.panel.name)
        messages.success(self.request, msg)
        return ret

    def get_success_url(self):
        return reverse_lazy('panels:evaluation', kwargs={
            'pk': self.kwargs['pk'],
            'gene_symbol': self.gene_symbol
        })


class PanelEditGeneView(GELReviewerRequiredMixin, UpdateView):
    template_name = "panels/genepanel_edit_gene.html"

    form_class = PanelGeneForm
    gene_symbol = None

    def get_object(self):
        return self.panel.get_gene(self.kwargs['gene_symbol'])

    @cached_property
    def panel(self):
        return GenePanel.objects.get_active_panel(pk=self.kwargs['pk'])

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['panel'] = self.panel
        kwargs['request'] = self.request
        kwargs['initial'] = self.object.get_form_initial()
        return kwargs

    def get_context_data(self, *args, **kwargs):
        ctx = super().get_context_data(*args, **kwargs)
        ctx['panel'] = self.panel
        return ctx

    def form_valid(self, form):
        form.save_gene()
        self.gene_symbol = form.cleaned_data['gene'].gene_symbol
        ret = super().form_valid(form)
        msg = "Successfully changed gene information for panel {}".format(self.panel.panel.name)
        messages.success(self.request, msg)
        return ret

    def get_success_url(self):
        return reverse_lazy('panels:evaluation', kwargs={
            'pk': self.kwargs['pk'],
            'gene_symbol': self.gene_symbol
        })


class GenePanelSpanshotView(DetailView):
    template_name = "panels/genepanelsnapshot_detail.html"
    context_object_name = 'gene'

    def get_object(self):
        return self.panel.get_gene(self.kwargs['gene_symbol'])

    def get_context_data(self, *args, **kwargs):
        ctx = super().get_context_data(*args, **kwargs)
        ctx['panel'] = self.panel
        ctx['sharing_panels'] = GenePanelSnapshot.objects.get_gene_panels(self.kwargs['gene_symbol'])
        ctx['feedback_review_parts'] = [
            'Rating',
            'Mode of inheritance',
            'Mode of pathogenicity',
            'Publications',
            'Phenotypes'
        ]
        ctx['form'] = GeneReviewForm(
            panel=self.panel,
            request=self.request,
            gene=self.object
        )
        ctx['form_edit'] = PanelGeneForm(
            instance=self.object,
            initial=self.object.get_form_initial(),
            panel=self.panel,
            request=self.request
        )

        ctx['gene_ready_form'] = GeneReadyForm(
            instance=self.object,
            initial={},
            request=self.request,
        )

        ctx['edit_gene_tags_form'] = UpdateGeneTagsForm(instance=self.object)
        ctx['edit_gene_mop_form'] = UpdateGeneMOPForm(instance=self.object)
        ctx['edit_gene_moi_form'] = UpdateGeneMOIForm(instance=self.object)
        ctx['edit_gene_phenotypes_form'] = UpdateGenePhenotypesForm(instance=self.object)
        ctx['edit_gene_publications_form'] = UpdateGenePublicationsForm(instance=self.object)
        ctx['edit_gene_rating_form'] = UpdateGeneRatingForm(instance=self.object)

        ctx['panel_genes'] = list(self.panel.get_all_entries)
        cgi = ctx['panel_genes'].index(self.object)
        ctx['next_gene'] = None if cgi == len(ctx['panel_genes']) - 1 else ctx['panel_genes'][cgi + 1]
        ctx['prev_gene'] = None if cgi == 0 else ctx['panel_genes'][cgi - 1]
        ctx['updated'] = False

        return ctx

    @cached_property
    def panel(self):
        return GenePanel.objects.get_active_panel(pk=self.kwargs['pk'])


class PanelMarkNotReadyView(GELReviewerRequiredMixin, PanelMixin, ActAndRedirectMixin, DetailView):
    model = GenePanelSnapshot

    def act(self):
        self.get_object().mark_genes_not_ready()


class GeneReviewView(VerifiedReviewerRequiredMixin, UpdateView):
    template_name = "panels/genepanel_edit_gene.html"
    context_object_name = 'gene'

    form_class = GeneReviewForm

    def get_object(self):
        return self.panel.get_gene(self.kwargs['gene_symbol'])

    @cached_property
    def panel(self):
        return GenePanel.objects.get_active_panel(pk=self.kwargs['pk'])

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['panel'] = self.panel
        kwargs['request'] = self.request
        kwargs['gene'] = self.object
        kwargs['initial'] = {}
        kwargs['instance'] = None
        return kwargs

    def get_context_data(self, *args, **kwargs):
        ctx = super().get_context_data(*args, **kwargs)
        ctx['panel'] = self.panel.panel
        return ctx

    def form_valid(self, form):
        ret = super().form_valid(form)
        msg = "Successfully reviewed gene {}".format(self.get_object().gene.get('gene_symbol'))
        messages.success(self.request, msg)
        return ret

    def get_success_url(self):
        return reverse_lazy('panels:evaluation', kwargs={
            'pk': self.kwargs['pk'],
            'gene_symbol': self.kwargs['gene_symbol']
        })


class MarkGeneReadyView(GELReviewerRequiredMixin, UpdateView):
    template_name = None  # it should only accept a POST request anyway
    form_class = GeneReadyForm

    def get_object(self):
        return self.panel.get_gene(self.kwargs['gene_symbol'])

    @cached_property
    def panel(self):
        return GenePanel.objects.get_active_panel(pk=self.kwargs['pk'])

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        kwargs['initial'] = {}
        return kwargs

    def form_valid(self, form):
        ret = super().form_valid(form)
        msg = "{} marked as ready".format(self.get_object().gene.get('gene_symbol'))
        messages.success(self.request, msg)
        return ret

    def get_success_url(self):
        return reverse_lazy('panels:evaluation', kwargs={
            'pk': self.kwargs['pk'],
            'gene_symbol': self.kwargs['gene_symbol']
        })


class MarkGeneNotReadyView(GELReviewerRequiredMixin, UpdateView):
    def get_object(self):
        return self.panel.get_gene(self.kwargs['gene_symbol'])

    @cached_property
    def panel(self):
        return GenePanel.objects.get_active_panel(pk=self.kwargs['pk'])

    def post(self, *args, **kwargs):
        self.object = self.get_object()
        self.object.ready = False
        self.object.save()

        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse_lazy('panels:evaluation', kwargs={
            'pk': self.kwargs['pk'],
            'gene_symbol': self.kwargs['gene_symbol']
        })


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
        response['Content-Disposition'] = 'attachment; filename=' + panel_name + '.tsv'
        writer = csv.writer(response, delimiter='\t')

        writer.writerow((
            "Gene_Symbol", "Sources(; separated)", "Level4", "Level3", "Level2", "Model_Of_Inheritance",
            "Phenotypes",
            "Omim", "Orphanet", "HPO", "Publications", "Description", "Flagged", "GEL_Status",
            "UserRatings_Green_amber_red", "version", "ready", "Mode of pathogenicity"))

        categories = self.get_categories()
        for gpentry in self.object.get_all_entries:
            if not gpentry.flagged and str(gpentry.status) in categories:
                amber_perc, green_perc, red_prec = gpentry.aggregate_ratings()

                evidence = ";".join([evidence.name for evidence in gpentry.evidence.all()])
                export_gpentry = (gpentry.gene.get('gene_symbol'), evidence,
                                  panel_name, self.object.level4title.level3title,
                                  self.object.level4title.level2title,
                                  "", gpentry.moi,
                                  ";".join(map(remove_non_ascii, gpentry.phenotypes)),
                                  ";".join(map(remove_non_ascii, self.object.level4title.omim)),
                                  ";".join(map(remove_non_ascii, self.object.level4title.orphanet)),
                                  ";".join(map(remove_non_ascii, self.object.level4title.hpo)),
                                  ";".join(map(remove_non_ascii, gpentry.publications)),
                                  "", str(gpentry.flagged), str(gpentry.saved_gel_status),
                                  ";".join(map(str, [green_perc, amber_perc, red_prec])),
                                  str(version),
                                  gpentry.ready, gpentry.mode_of_pathogenicity)
                writer.writerow(export_gpentry)

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
        all = True if self.request.user.is_authenticated and self.request.user.reviewer.is_GEL() else False
        kwargs['panels'] = GenePanelSnapshot.objects.get_active(all)
        return kwargs

    def get_context_data(self, *args, **kwargs):
        ctx = super().get_context_data()

        if self.kwargs.get('panel_1_id') and self.kwargs.get('panel_2_id'):
            ctx['panel_1'] = panel_1 = GenePanel.objects.get_panel(pk=self.kwargs['panel_1_id']).active_panel
            ctx['panel_2'] = panel_2 = GenePanel.objects.get_panel(pk=self.kwargs['panel_2_id']).active_panel

            panel_1_items = {e.gene.get('gene_symbol'): e for e in panel_1.get_all_entries}
            panel_2_items = {e.gene.get('gene_symbol'): e for e in panel_2.get_all_entries}

            all = list(set(panel_1_items.keys()) | set(panel_2_items.keys()))
            all.sort()

            intersection = list(set(panel_1_items.keys() & set(panel_2_items.keys())))
            ctx['show_copy_reviews'] = self.request.user.reviewer.is_GEL() and len(intersection) > 0

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
        all = True if self.request.user.is_authenticated and self.request.user.reviewer.is_GEL() else False
        kwargs['panels'] = GenePanelSnapshot.objects.get_active(all)
        return kwargs

    def get_context_data(self, *args, **kwargs):
        ctx = super().get_context_data()
        gene_symbol = self.kwargs['gene_symbol']
        ctx['gene_symbol'] = gene_symbol

        ctx['panel_1'] = panel_1 = GenePanel.objects.get_panel(pk=self.kwargs['panel_1_id']).active_panel
        ctx['panel_2'] = panel_2 = GenePanel.objects.get_panel(pk=self.kwargs['panel_2_id']).active_panel
        ctx['panel_1_entry'] = panel_1.get_gene(gene_symbol)
        ctx['panel_2_entry'] = panel_2.get_gene(gene_symbol)

        return ctx


class CopyReviewsView(GELReviewerRequiredMixin, FormView):
    template_name = 'panels/compare/copy_reviews.html'
    form_class = CopyReviewsForm

    def form_valid(self, form):
        ctx = self.get_context_data()
        total_count = form.copy_reviews(ctx['intersection'], ctx['panel_1'], ctx['panel_2'])

        messages.success(self.request, "{} review{} copied".format(total_count, pluralize(total_count)))
        return redirect(reverse_lazy('panels:compare', args=(ctx['panel_1'].panel.pk, ctx['panel_2'].panel.pk)))

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['initial'] = {
            'panel_1': GenePanel.objects.get_panel(pk=self.kwargs['panel_1_id']).active_panel.pk,
            'panel_2': GenePanel.objects.get_panel(pk=self.kwargs['panel_2_id']).active_panel.pk
        }
        return kwargs

    def form_invalid(self, form):
        return super().form_invalid(form)

    def get_context_data(self, *args, **kwargs):
        ctx = super().get_context_data(*args, **kwargs)

        ctx['panel_1'] = panel_1 = GenePanel.objects.get_panel(pk=self.kwargs['panel_1_id']).active_panel
        ctx['panel_2'] = panel_2 = GenePanel.objects.get_panel(pk=self.kwargs['panel_2_id']).active_panel

        panel_1_items = {e.gene.get('gene_symbol'): e for e in panel_1.get_all_entries}
        panel_2_items = {e.gene.get('gene_symbol'): e for e in panel_2.get_all_entries}

        intersection = list(set(panel_1_items.keys() & set(panel_2_items.keys())))
        intersection.sort()
        ctx['intersection'] = intersection

        comparison = [[gene, panel_1_items[gene], panel_2_items[gene]] for gene in intersection]
        ctx['comparison'] = comparison

        return ctx


class DownloadAllGenes(GELReviewerRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        response = HttpResponse(content_type='text/tab-separated-values')
        attachment = 'attachment; filename=All_genes_{}.tsv'.format(datetime.now().strftime('%Y%M%D%H%i'))
        response['Content-Disposition'] = attachment
        writer = csv.writer(response, delimiter='\t')
        writer.writerow((
            "Symbol",
            "Panel",
            "Panel Version",
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

        ))
        entries = GenePanelEntrySnapshot.objects\
            .get_active()\
            .prefetch_related('tags', 'evidence', 'panel__panel')\
            .all()

        for entry in entries:

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
                entry.panel.version,
                colour,
                ';'.join([evidence.name for evidence in entry.evidence.all()]),
                entry.moi,
                entry.mode_of_pathogenicity,
                ';'.join([tag.name for tag in entry.tags.all()]),
                entry.gene.get('GRch37', {}).get('ensemble_id', '-'),
                entry.gene.get('GRch38', {}).get('ensemble_id', '-'),
                entry.gene.get('biotype', '-'),
                phenotypes,
                entry.gene.get('GRch37', {}).get('location', '-'),
                entry.gene.get('GRch38', {}).get('location', '-'),
            ]
            writer.writerow(row)

        return response


class DownloadAllPanels(GELReviewerRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        response = HttpResponse(content_type='text/tab-separated-values')
        attachment = 'attachment; filename=All_panels_{}.tsv'.format(datetime.now().strftime('%Y%M%D%H%i'))
        response['Content-Disposition'] = attachment
        writer = csv.writer(response, delimiter='\t')

        writer.writerow((
            "Level 4 title",
            "Level 3 title",
            "Level 2 title",
            "URL",
            "Current Version",
            "# rated genes/total genes",
            "#reviewers",
            "Reviewer name and affiliation (;)",
            "Reviewer emails (;)",
            "Approved",
            "Relevant disorders"
        ))

        panels = GenePanelSnapshot.objects\
            .get_active_anotated()\
            .prefetch_related(
                'genepanelentrysnapshot_set',
                'genepanelentrysnapshot_set__evaluation',
                'genepanelentrysnapshot_set__evaluation__user',
                'genepanelentrysnapshot_set__evaluation__user__reviewer',
            )\
            .all()

        for panel in panels:
            rate = "{} of {} genes reviewed".format(panel.number_of_evaluated_genes, panel.number_of_genes)
            reviewers = panel.contributors

            row = [
                panel.level4title.name,
                panel.level4title.level3title,
                panel.level4title.level2title,
                request.build_absolute_uri(reverse('panels:detail', args=(panel.panel.id,))),
                panel.version,
                rate,
                len(reviewers),
                ";".join(["{} {} ({})".format(user[0], user[1], user[3]) for user in reviewers]),  # aff
                ";".join([user[2] for user in reviewers if user[2]]),  # email
                panel.panel.approved,
                ";".join(panel.old_panels)
            ]
            writer.writerow(row)

        return response


class ActivityListView(ListView):
    model = Activity
    context_object_name = 'activities'
    paginate_by = 200

    def get_queryset(self, *args, **kwargs):
        qs = super().get_queryset(*args, **kwargs)
        qs = qs.prefetch_related('user', 'panel', 'user__reviewer')
        return qs
