from django.views.generic.base import View
from django.shortcuts import render
from django.utils.functional import cached_property
from django_ajax.mixin import AJAXMixin
from panelapp.mixins import GELReviewerRequiredMixin
from .forms import PanelGeneForm
from .models import GenePanel
from .models import GenePanelSnapshot


class BaseAjaxGeneMixin:
    def process(self):
        raise NotImplementedError

    def get(self, request, *args, **kwargs):
        self.process()
        return self.return_data()

    def post(self, request, *args, **kwargs):
        self.process()
        return self.return_data()

    @cached_property
    def panel(self):
        return GenePanel.objects.get(pk=self.kwargs['pk']).active_panel


class GeneClearDataAjaxMixin(BaseAjaxGeneMixin):
    template_name = 'panels/genepanelentrysnapshot/details.html'

    def return_data(self):
        details = render(self.request, self.template_name, {
            'gene': self.gene,
            'panel': self.panel,
            'sharing_panels': GenePanelSnapshot.objects.get_gene_panels(self.kwargs['gene_symbol']),
            'form_edit': PanelGeneForm(
                instance=self.gene,
                initial=self.gene.get_form_initial(),
                panel=self.panel,
                request=self.request
            )
        })

        return {
            'inner-fragments': {
                '#details': details
            }
        }

    @cached_property
    def gene(self):
        return self.panel.get_gene(self.kwargs['gene_symbol'])


class ClearPublicationsAjaxView(GELReviewerRequiredMixin, GeneClearDataAjaxMixin, AJAXMixin, View):
    def process(self):
        self.gene.publications = []
        self.gene.save()
        del self.gene


class ClearPhoenotypesAjaxView(GELReviewerRequiredMixin, GeneClearDataAjaxMixin, AJAXMixin, View):
    def process(self):
        self.gene.phenotypes = []
        self.gene.save()
        del self.gene


class ClearModeOfPathogenicityAjaxView(GELReviewerRequiredMixin, GeneClearDataAjaxMixin, AJAXMixin, View):
    def process(self):
        self.gene.mode_of_pathogenicity = ""
        self.gene.save()
        del self.gene


class ClearSourcesAjaxView(GELReviewerRequiredMixin, GeneClearDataAjaxMixin, AJAXMixin, View):
    def process(self):
        self.gene.clear_evidences(self.request.user)
        del self.panel
        del self.gene


class ClearSingleSourceAjaxView(GELReviewerRequiredMixin, GeneClearDataAjaxMixin, AJAXMixin, View):
    def process(self):
        self.gene.clear_evidences(self.request.user, evidence=self.kwargs['source'])
        del self.panel
        del self.gene


class PanelAjaxMixin(BaseAjaxGeneMixin):
    template_name = "panels/genepanel_list_table.html"

    def return_data(self):
        ctx = {
            'panels': GenePanelSnapshot.objects.get_active()
        }
        table = render(self.request, self.template_name, ctx)
        return {
            'inner-fragments': {
                '#table': table
            }
        }


class DeletePanelAjaxView(GELReviewerRequiredMixin, PanelAjaxMixin, AJAXMixin, View):
    def process(self):
        GenePanel.objects.get(pk=self.kwargs['pk']).delete()


class RejectPanelAjaxView(GELReviewerRequiredMixin, PanelAjaxMixin, AJAXMixin, View):
    def process(self):
        GenePanel.objects.get(pk=self.kwargs['pk']).reject()


class ApprovePanelAjaxView(GELReviewerRequiredMixin, PanelAjaxMixin, AJAXMixin, View):
    def process(self):
        GenePanel.objects.get(pk=self.kwargs['pk']).approve()


class DeleteGeneAjaxView(GELReviewerRequiredMixin, BaseAjaxGeneMixin, AJAXMixin, View):
    template_name = "panels/genepanel_table.html"

    def process(self):
        self.panel.delete_gene(self.kwargs['gene_symbol'])

    def return_data(self):
        ctx = {
            'panel': self.panel
        }
        table = render(self.request, self.template_name, ctx)
        return {
            'inner-fragments': {
                '#table': table
            }
        }


class GeneObjectMixin:
    @cached_property
    def gene(self):
        return self.panel.get_gene(self.kwargs['gene_symbol'])


class UpdateGeneTagsAjaxView(GELReviewerRequiredMixin, GeneObjectMixin, BaseAjaxGeneMixin, AJAXMixin, View):
    template_name = "panels/genepanelentrysnapshot/review/part_tags.html"

    def process(self):
        pass

    def return_data(self):
        pass
