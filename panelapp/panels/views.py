from django.contrib.auth.mixins import LoginRequiredMixin
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
from .forms import UploadGenesForm
from .forms import UploadPanelsForm
from .forms import UploadReviewsForm
from .forms import PanelForm
from .models import Gene
from .models import GenePanel
from .models import GenePanelSnapshot


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


class UpdatePanelView(GELReviewerRequiredMixin, UpdateView):
    template_name = "panels/genepanel_create.html"
    form_class = PanelForm

    def get_object(self, *args, **kwargs):
        return GenePanel.objects.get(pk=self.kwargs['pk']).active_panel

    def form_valid(self, form):
        self.instance = form.instance
        ret = super().form_valid(form)
        messages.success(self.request, "Successfully updated the panel")
        return ret

    def get_success_url(self):
        return reverse_lazy('panels:detail', kwargs={'pk': self.get_object().panel.pk})


class GenePanelView(DetailView):
    model = GenePanel

    def get_context_data(self, *args, **kwargs):
        ctx = super().get_context_data(*args, **kwargs)
        ctx['panel'] = self.object.active_panel
        ctx['edit'] = PanelForm(initial=ctx['panel'].get_form_initial())
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
