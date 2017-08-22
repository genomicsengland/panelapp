from django import forms
from panels.models import UploadedGeneList
from panels.models import UploadedReviewsList
from panels.models import UploadedPanelList
from panels.models import GenePanel
from .panel import PanelForm  # noqa
from .promotepanel import PromotePanelForm  # noqa
from .panelgene import PanelGeneForm  # noqa
from .genereview import GeneReviewForm  # noqa
from .geneready import GeneReadyForm  # noqa
from panels.exceptions import UserDoesNotExist
from panels.exceptions import GeneDoesNotExist
from panels.exceptions import TSVIncorrectFormat


class UploadGenesForm(forms.Form):
    gene_list = forms.FileField(label='Select a file', required=True)

    def process_file(self, **kwargs):
        gene_list = UploadedGeneList.objects.create(gene_list=self.cleaned_data['gene_list'])
        gene_list.create_genes()


class UploadPanelsForm(forms.Form):
    panel_list = forms.FileField(label='Select a file', required=True)

    def process_file(self, **kwargs):
        panel_list = UploadedPanelList.objects.create(panel_list=self.cleaned_data['panel_list'])
        try:
            panel_list.process_file(kwargs.pop('user'))
        except GeneDoesNotExist as e:
            message = 'Line: {} has a wrong gene, please check it and try again.'.format(e)
            raise forms.ValidationError(message)
        except UserDoesNotExist as e:
            message = 'Line: {} has a wrong username, please check it and try again.'.format(e)
            raise forms.ValidationError(message)
        except TSVIncorrectFormat as e:
            message = "Line: {} is not properly formatted, please check it and try again.".format(e)
            raise forms.ValidationError(message)


class UploadReviewsForm(forms.Form):
    review_list = forms.FileField(label='Select a file', required=True)

    def process_file(self, **kwargs):
        review_list = UploadedReviewsList.objects.create(reviews=self.cleaned_data['review_list'])
        try:
            review_list.process_file()
        except GeneDoesNotExist as e:
            message = 'Line: {} has a wrong gene, please check it and try again.'.format(e)
            raise forms.ValidationError(message)
        except UserDoesNotExist as e:
            message = 'Line: {} has a wrong username, please check it and try again.'.format(e)
            raise forms.ValidationError(message)
        except TSVIncorrectFormat as e:
            message = "Line: {} is not properly formatted, please check it and try again.".format(e)
            raise forms.ValidationError(message)


class ComparePanelsForm(forms.Form):
    panels = GenePanel.objects.none()
    panel_1 = forms.ModelChoiceField(queryset=panels, widget=forms.Select(attrs={'class': 'form-control'}))
    panel_2 = forms.ModelChoiceField(queryset=panels, widget=forms.Select(attrs={'class': 'form-control'}))

    def __init__(self, *args, **kwargs):
        qs = None

        try:
            qs = kwargs.pop('panels')
        except KeyError:
            pass

        super(ComparePanelsForm, self).__init__(*args, **kwargs)
        if qs:
            self.fields['panel_1'].queryset = qs
            self.fields['panel_2'].queryset = qs


class CopyReviewsForm(forms.Form):
    panel_1 = forms.CharField(required=True, widget=forms.widgets.HiddenInput())
    panel_2 = forms.CharField(required=True, widget=forms.widgets.HiddenInput())

    def copy_reviews(self, gene_symbols, panel_1, panel_2):
        count = 0

        for gene in gene_symbols:
            count += self.copy_gene_evaluations(gene, panel_1, panel_2)

        return count

    def copy_gene_evaluations(self, gene, panel_1, panel_2):
        count = 0

        source_entry = panel_1.get_gene(gene)
        destination_entry = panel_2.get_gene(gene)
        panel_name = panel_1.level4title.name

        if source_entry and destination_entry:
            source_evaluations = source_entry.evaluation.all()
            for ev in source_evaluations:
                version = ev.version if ev.version else '0'
                ev.version = "Imported from {} panel version {}".format(panel_name, version)

            count = self.add_evaluation_list(gene, destination_entry, source_evaluations)

        return count

    def add_evaluation_list(self, gene, destination_entry, source_evaluations):
        destination_users = destination_entry.evaluation.values_list('user', flat=True)
        filtered_evaluations = [ev for ev in source_evaluations if ev.user.pk not in destination_users]

        for ev in filtered_evaluations:
            ev.pk = None
            ev.save()
            destination_entry.evaluation.add(ev)

        return len(filtered_evaluations)
