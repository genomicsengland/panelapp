from django import forms
from panels.models import UploadedGeneList
from .panel import PanelForm  # noqa
from .promotepanel import PromotePanelForm  # noqa
from .panelgene import PanelGeneForm  # noqa
from .genereview import GeneReviewForm  # noqa


class UploadGenesForm(forms.Form):
    gene_list = forms.FileField(label='Select a file', required=True)

    def process_file(self):
        gene_list = UploadedGeneList.objects.create(gene_list=self.cleaned_data['gene_list'])
        gene_list.create_genes()


class UploadPanelsForm(forms.Form):
    panel_list = forms.FileField(label='Select a file', required=True)

    def process_file(self):
        print('processing upload genes form')


class UploadReviewsForm(forms.Form):
    review_list = forms.FileField(label='Select a file', required=True)

    def process_file(self):
        print('processing upload genes form')
