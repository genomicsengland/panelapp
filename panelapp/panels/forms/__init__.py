from django import forms
from panels.models import UploadedGeneList
from panels.models import GenePanel
from .panel import PanelForm  # noqa
from .promotepanel import PromotePanelForm  # noqa
from .panelgene import PanelGeneForm  # noqa
from .genereview import GeneReviewForm  # noqa
from .geneready import GeneReadyForm  # noqa


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


class ComparePanelsForm(forms.Form):
    panels = GenePanel.objects.none()
    panel_1 = forms.ModelChoiceField(queryset = panels, widget=forms.Select(attrs={'class': 'form-control'}))
    panel_2 = forms.ModelChoiceField(queryset = panels, widget=forms.Select(attrs={'class': 'form-control'}))

    def __init__(self, *args, **kwargs):
        qs = kwargs.pop('panels')
        super(ComparePanelsForm, self).__init__(*args, **kwargs)
        self.fields['panel_1'].queryset = qs
        self.fields['panel_2'].queryset = qs
