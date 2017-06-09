from django.contrib import messages
from django.views.generic import TemplateView
from django.views.generic.base import View
from django.views.generic import FormView
from django.views.generic import ListView
from django.views.generic import UpdateView
from django.views.generic import DetailView
from django.views.generic import CreateView
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.functional import cached_property

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
from .forms.ajax import UpdateGeneTagsForm
from .forms.ajax import UpdateGeneMOPForm
from .forms.ajax import UpdateGeneMOIForm
from .forms.ajax import UpdateGenePhenotypesForm
from .forms.ajax import UpdateGenePublicationsForm
from .forms.ajax import UpdateGeneRatingForm
from .models import Gene
from .models import GenePanel
from .models import GenePanelSnapshot
from .models import GenePanelEntrySnapshot
from .mixins import PanelMixin
from .mixins import ActAndRedirectMixin


class EmptyView(View):
    pass


class PanelsIndexView(ListView):
    template_name = "panels/genepanel_list.html"
    model = GenePanelSnapshot
    context_object_name = 'panels'

    def get_queryset(self, *args, **kwargs):
        if self.request.GET.get('gene'):
            return GenePanelSnapshot.objects.get_gene_panels(self.request.GET.get('gene'))
        else:
            return GenePanelSnapshot.objects.get_active()

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
        return reverse_lazy('panels:detail', kwargs={'pk': self.instance.pk})


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
        form.process_file()
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
        ctx['gene_symbol'] = self.kwargs['slug']
        ctx['entries'] = GenePanelEntrySnapshot.objects.get_gene_panels(self.kwargs['slug'])
        return ctx


class GeneListView(ListView):
    model = Gene
    context_object_name = "genes"


class PromotePanelView(GELReviewerRequiredMixin, PanelMixin, UpdateView):
    form_class = PromotePanelForm

    def form_valid(self, form):
        ret = super().form_valid(form)
        self.instance = form.instance.panel
        messages.success(self.request, "Successfully upgraded Panel {}".format(self.get_object().name))
        return ret


class PanelAddGeneView(VerifiedReviewerRequiredMixin, CreateView):
    template_name = "panels/genepanel_add_gene.html"

    form_class = PanelGeneForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['panel'] = GenePanel.objects.get(pk=self.kwargs['pk']).active_panel
        kwargs['request'] = self.request
        return kwargs

    def get_context_data(self, *args, **kwargs):
        ctx = super().get_context_data(*args, **kwargs)
        ctx['panel'] = self.panel
        return ctx

    @property
    def panel(self):
        return GenePanel.objects.get(pk=self.kwargs['pk']).active_panel

    def form_valid(self, form):
        ret = super().form_valid(form)
        msg = "Successfully added a new gene to the panel {}".format(self.object.panel.panel.name)
        messages.success(self.request, msg)
        return ret

    def get_success_url(self):
        return reverse_lazy('panels:evaluation', kwargs={
            'pk': self.kwargs['pk'],
            'gene_symbol': self.object.gene_core.gene_symbol
        })


class PanelEditGeneView(GELReviewerRequiredMixin, UpdateView):
    template_name = "panels/genepanel_edit_gene.html"

    form_class = PanelGeneForm

    def get_object(self):
        return self.panel.get_gene(self.kwargs['gene_symbol'])

    @cached_property
    def panel(self):
        return GenePanel.objects.get(pk=self.kwargs['pk']).active_panel

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
        ret = super().form_valid(form)
        msg = "Successfully changed gene information for panel {}".format(self.object.panel.panel.name)
        messages.success(self.request, msg)
        return ret

    def get_success_url(self):
        return reverse_lazy('panels:evaluation', kwargs={
            'pk': self.kwargs['pk'],
            'gene_symbol': self.object.gene_core.gene_symbol
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

        return ctx

    @cached_property
    def panel(self):
        return GenePanel.objects.get(pk=self.kwargs['pk']).active_panel


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
        return GenePanel.objects.get(pk=self.kwargs['pk']).active_panel

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
        return GenePanel.objects.get(pk=self.kwargs['pk']).active_panel

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
