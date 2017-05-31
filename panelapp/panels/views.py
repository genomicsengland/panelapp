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

from panelapp.mixins import GELReviewerRequiredMixin
from panelapp.mixins import VerifiedReviewerRequiredMixin
from accounts.models import User
from .forms import UploadGenesForm
from .forms import UploadPanelsForm
from .forms import UploadReviewsForm
from .forms import PanelForm
from .forms import PromotePanelForm
from .forms import PanelAddGeneForm
from .models import Gene
from .models import GenePanel
from .models import GenePanelSnapshot
from .mixins import PanelMixin


class EmptyView(View):
    pass


class PanelsIndexView(ListView):
    template_name = "panels/genepanel_list.html"
    model = GenePanelSnapshot
    queryset = GenePanelSnapshot.objects.get_active()
    context_object_name = 'panels'

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


class GeneListView(ListView):
    model = Gene
    context_object_name = 'genes'


class PromotePanelView(GELReviewerRequiredMixin, PanelMixin, UpdateView):
    form_class = PromotePanelForm

    def form_valid(self, form):
        ret = super().form_valid(form)
        self.instance = form.instance.panel
        messages.success(self.request, "Successfully upgraded Panel {}".format(self.get_object().name))
        return ret


class PanelAddGeneView(VerifiedReviewerRequiredMixin, CreateView):
    template_name = "panels/genepanel_add_gene.html"
    form_class = PanelAddGeneForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['panel'] = GenePanel.objects.get(pk=self.kwargs['pk']).active_panel
        kwargs['request'] = self.request
        return kwargs

    def get_context_data(self, *args, **kwargs):
        ctx = super().get_context_data(*args, **kwargs)
        ctx['panel'] = GenePanel.objects.get(pk=self.kwargs['pk']).active_panel
        self.panel = ctx['panel']
        return ctx

    def form_valid(self, form):
        ret = super().form_valid(form)
        messages.success(self.request, "Successfully added a new gene to the panel {}".format(self.object.panel.panel.name))
        return ret

    def get_success_url(self):
        return reverse_lazy('panels:evaluation', kwargs={
            'pk': self.object.panel.panel.pk,
            'gene_symbol': self.object.gene.get('gene_name')
        })
