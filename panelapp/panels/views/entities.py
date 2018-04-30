from django.http import Http404
from django.contrib import messages
from django.views.generic import DetailView, RedirectView
from django.views.generic import CreateView
from django.utils.functional import cached_property
from django.views.generic import UpdateView
from django.urls import reverse_lazy
from django.shortcuts import redirect
from django.views.generic import TemplateView
from panelapp.mixins import GELReviewerRequiredMixin
from panelapp.mixins import VerifiedReviewerRequiredMixin
from panels.forms import GeneReviewForm
from panels.forms import STRReviewForm
from panels.forms import PanelGeneForm
from panels.forms import GeneReadyForm
from panels.forms import PanelSTRForm
from panels.forms import STRReadyForm
from panels.forms.ajax import UpdateGeneTagsForm
from panels.forms.ajax import UpdateGeneMOPForm
from panels.forms.ajax import UpdateGeneMOIForm
from panels.forms.ajax import UpdateGenePhenotypesForm
from panels.forms.ajax import UpdateGenePublicationsForm
from panels.forms.ajax import UpdateGeneRatingForm
from panels.forms.ajax import UpdateSTRTagsForm
from panels.forms.ajax import UpdateSTRMOIForm
from panels.forms.ajax import UpdateSTRPhenotypesForm
from panels.forms.ajax import UpdateSTRPublicationsForm
from panels.forms.ajax import UpdateSTRRatingForm
from panels.mixins import PanelMixin
from panels.mixins import ActAndRedirectMixin
from panels.models import GenePanel
from panels.models import GenePanelSnapshot
from panels.models import GenePanelEntrySnapshot


class EchoWriter(object):
    def write(self, value):
        return value


class EntityMixin:
    def is_gene(self):
        return 'gene' == self.kwargs['entity_type']

    def is_str(self):
        return 'str' == self.kwargs['entity_type']

    def get_object(self):
        try:
            if self.is_gene():
                if self.request.GET.get('pk'):
                    return self.panel.get_gene_by_pk(self.request.GET.get('pk'), prefetch_extra=True)
                else:
                    return self.panel.get_gene(self.kwargs['entity_name'], prefetch_extra=True)
            elif self.is_str():
                return self.panel.get_str(self.kwargs['entity_name'], prefetch_extra=True)
        except GenePanelEntrySnapshot.DoesNotExist:
            raise Http404


class GenePanelSpanshotView(EntityMixin, DetailView):
    template_name = "panels/genepanelsnapshot_detail.html"
    context_object_name = 'entity'

    def get_context_data_gene(self, ctx):
        form_initial = {}
        if self.request.user.is_authenticated:
            user_review = self.object.review_by_user(self.request.user)
            if user_review:
                form_initial = user_review.dict_tr()
                form_initial['comments'] = None

        ctx['form'] = GeneReviewForm(
            panel=self.panel,
            request=self.request,
            gene=self.object,
            initial=form_initial
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

        ctx['edit_entity_tags_form'] = UpdateGeneTagsForm(instance=self.object)
        ctx['edit_entity_mop_form'] = UpdateGeneMOPForm(instance=self.object)
        ctx['edit_entity_moi_form'] = UpdateGeneMOIForm(instance=self.object)
        ctx['edit_entity_phenotypes_form'] = UpdateGenePhenotypesForm(instance=self.object)
        ctx['edit_entity_publications_form'] = UpdateGenePublicationsForm(instance=self.object)
        ctx['edit_entity_rating_form'] = UpdateGeneRatingForm(instance=self.object)

        cgi = ctx['panel_genes'].index(self.object)
        ctx['next_gene'] = None if cgi == len(ctx['panel_genes']) - 1 else ctx['panel_genes'][cgi + 1]
        ctx['prev_gene'] = None if cgi == 0 else ctx['panel_genes'][cgi - 1]

        ctx['feedback_review_parts'] = [
            'Rating',
            'Mode of inheritance',
            'Mode of pathogenicity',
            'Publications',
            'Phenotypes'
        ]

        return ctx

    def get_context_data_str(self, ctx):
        form_initial = {}
        if self.request.user.is_authenticated:
            user_review = self.object.review_by_user(self.request.user)
            if user_review:
                form_initial = user_review.dict_tr()
                form_initial['comments'] = None

        ctx['form'] = STRReviewForm(
            panel=self.panel,
            request=self.request,
            str_item=self.object,
            initial=form_initial
        )
        ctx['form_edit'] = PanelSTRForm(
            instance=self.object,
            initial=self.object.get_form_initial(),
            panel=self.panel,
            request=self.request
        )

        ctx['entity_ready_form'] = STRReadyForm(
            instance=self.object,
            initial={},
            request=self.request,
        )

        ctx['edit_entity_tags_form'] = UpdateSTRTagsForm(instance=self.object)
        ctx['edit_entity_moi_form'] = UpdateSTRMOIForm(instance=self.object)
        ctx['edit_entity_phenotypes_form'] = UpdateSTRPhenotypesForm(instance=self.object)
        ctx['edit_entity_publications_form'] = UpdateSTRPublicationsForm(instance=self.object)
        ctx['edit_entity_rating_form'] = UpdateSTRRatingForm(instance=self.object)

        cgi = ctx['panel_strs'].index(self.object)
        ctx['next_str'] = None if cgi == len(ctx['panel_strs']) - 1 else ctx['panel_strs'][cgi + 1]
        ctx['prev_str'] = None if cgi == 0 else ctx['panel_strs'][cgi - 1]

        ctx['feedback_review_parts'] = [
            'Rating',
            'Mode of inheritance',
            'Publications',
            'Phenotypes'
        ]

        return ctx

    def get_context_data(self, *args, **kwargs):
        ctx = super().get_context_data(*args, **kwargs)
        ctx['panel'] = self.panel
        ctx['entity_type'] = self.kwargs['entity_type']
        ctx['entity_name'] = self.kwargs['entity_name']

        is_admin = self.request.user.is_authenticated and self.request.user.reviewer.is_GEL()

        # check if STR has a linked Gene
        if self.is_gene() or (self.object.gene and self.object.gene.get('gene_symbol')):
            ctx['sharing_panels'] = GenePanelSnapshot.objects.get_shared_panels(
                self.object.gene.get('gene_symbol'),
                all=is_admin,
                internal=is_admin
            )
        else:
            ctx['sharing_panels'] = []

        ctx['panel_genes'] = list(self.panel.get_all_genes_extra)
        ctx['panel_strs'] = list(self.panel.get_all_strs_extra)

        if self.is_gene():
            ctx = self.get_context_data_gene(ctx)
        elif self.is_str():
            ctx = self.get_context_data_str(ctx)

        ctx['updated'] = False

        return ctx

    @cached_property
    def panel(self):
        return GenePanel.objects.get_active_panel(pk=self.kwargs['pk'])


class ModifyEntityCommonMixin(EntityMixin):
    entity_name = None

    def get_form_class(self):
        if self.is_gene():
            return PanelGeneForm
        elif self.is_str():
            return PanelSTRForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['panel'] = self.panel
        kwargs['request'] = self.request
        if self.object:
            kwargs['initial'] = self.object.get_form_initial()
        return kwargs

    def get_context_data(self, *args, **kwargs):
        ctx = super().get_context_data(*args, **kwargs)
        ctx['panel'] = self.panel
        return ctx

    @property
    def panel(self):
        return GenePanel.objects.get_active_panel(pk=self.kwargs['pk'])

    def get_success_url(self):
        return reverse_lazy('panels:evaluation', kwargs={
            'pk': self.kwargs['pk'],
            'entity_type': self.kwargs['entity_type'],
            'entity_name': self.entity_name
        })


class PanelAddEntityView(ModifyEntityCommonMixin, VerifiedReviewerRequiredMixin, CreateView):
    def get_template_names(self):
        if self.is_gene():
            return "panels/genepanel_add_gene.html"
        elif self.is_str():
            return "panels/genepanel_add_str.html"

    def form_valid(self, form):
        label = ''
        if self.is_gene():
            form.save_gene()
            self.entity_name = form.cleaned_data['gene'].gene_symbol
            label = 'gene: {}'.format(self.entity_name)
        elif self.is_str():
            form.save_str()
            self.entity_name = form.cleaned_data['name']
            label = 'STR: {}'.format(self.entity_name)

        ret = super().form_valid(form)
        msg = "Successfully added a new {} to the panel {}".format(label,
                                                                   self.panel.panel.name)
        messages.success(self.request, msg)
        return ret


class PanelEditEntityView(ModifyEntityCommonMixin, GELReviewerRequiredMixin, UpdateView):
    def get_template_names(self):
        if self.is_gene():
            return "panels/gene_edit.html"
        elif self.is_str():
            return "panels/str_edit.html"

    def form_valid(self, form):
        label = ''
        if self.is_gene():
            form.save_gene()
            self.entity_name = form.cleaned_data['gene'].gene_symbol
            label = 'gene: {}'.format(self.entity_name)
        elif self.is_str():
            form.save_str()
            self.entity_name = form.cleaned_data['name']
            label = 'STR: {}'.format(self.entity_name)
        ret = super().form_valid(form)
        msg = "Successfully changed gene information for panel {}".format(label, self.panel.panel.name)
        messages.success(self.request, msg)
        return ret


class PanelMarkNotReadyView(GELReviewerRequiredMixin, PanelMixin, ActAndRedirectMixin, DetailView):
    model = GenePanelSnapshot

    def act(self):
        self.get_object().mark_entities_not_ready()


class MarkEntityReadyView(EntityMixin, GELReviewerRequiredMixin, UpdateView):
    template_name = None  # it should only accept a POST request anyway
    form_class = GeneReadyForm

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
        msg = "{} marked as ready".format(self.get_object().label)
        messages.success(self.request, msg)
        return ret

    def get_success_url(self):
        return reverse_lazy('panels:evaluation', kwargs={
            'pk': self.kwargs['pk'],
            'entity_type': self.kwargs['entity_type'],
            'entity_name': self.kwargs['entity_name']
        })


class MarkGeneNotReadyView(EntityMixin, GELReviewerRequiredMixin, UpdateView):
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
            'entity_type': self.kwargs['entity_type'],
            'entity_name': self.kwargs['entity_name']
        })


class EntityReviewView(VerifiedReviewerRequiredMixin, EntityMixin, UpdateView):
    context_object_name = 'entity'

    def get_form_class(self):
        if self.is_gene():
            return GeneReviewForm
        elif self.is_str():
            return STRReviewForm

    def get_template_names(self):
        if self.is_gene():
            return "panels/gene_edit.html"
        elif self.is_str():
            return "panels/str_edit.html"

    def get_object(self):
        if self.is_gene():
            return self.panel.get_gene(self.kwargs['entity_name'], prefetch_extra=True)
        elif self.is_str():
            return self.panel.get_str(self.kwargs['entity_name'], prefetch_extra=True)

    @cached_property
    def panel(self):
        return GenePanel.objects.get_active_panel(pk=self.kwargs['pk'])

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['panel'] = self.panel
        kwargs['request'] = self.request

        if self.is_gene():
            kwargs['gene'] = self.object
        elif self.is_str():
            kwargs['str_item'] = self.object

        if not kwargs['initial']:
            kwargs['initial'] = {}
            if self.request.user.is_authenticated:
                user_review = self.object.review_by_user(self.request.user)
                if user_review:
                    kwargs['initial'] = user_review.dict_tr()
                    kwargs['initial']['comments'] = None
        kwargs['instance'] = None
        return kwargs

    def get_context_data(self, *args, **kwargs):
        ctx = super().get_context_data(*args, **kwargs)
        ctx['panel'] = self.panel.panel
        return ctx

    def form_valid(self, form):
        ret = super().form_valid(form)
        if self.is_gene():
            msg = "Successfully reviewed gene {}".format(self.kwargs['entity_name'])
        elif self.is_str():
            msg = "Successfully reviewed STR {}".format(self.kwargs['entity_name'])
        messages.success(self.request, msg)
        return ret

    def get_success_url(self):
        return reverse_lazy('panels:evaluation', kwargs={
            'pk': self.kwargs['pk'],
            'entity_type': self.kwargs['entity_type'],
            'entity_name': self.kwargs['entity_name']
        })


class RedirectGenesToEntities(RedirectView):
    """Redirect URL schema which was supported before, i.e. /panels/<pk>/<gene_symbol>"""

    def dispatch(self, request, *args, **kwargs):
        self.url = reverse_lazy('panels:evaluation', kwargs={
            'pk': self.kwargs['pk'],
            'entity_type': 'gene',
            'entity_name': self.kwargs['entity_name']
        })
        return super().dispatch(request, *args, **kwargs)
