from django import forms
from django.db import transaction
from panels.models import UploadedGeneList
from panels.models import UploadedReviewsList
from panels.models import UploadedPanelList
from panels.models import GenePanel
from .panel import PanelForm  # noqa
from .promotepanel import PromotePanelForm  # noqa
from .panelgene import PanelGeneForm  # noqa
from .genereview import GeneReviewForm  # noqa
from .geneready import GeneReadyForm  # noqa
from panels.models import ProcessingRunCode
from panels.exceptions import UserDoesNotExist
from panels.exceptions import GeneDoesNotExist
from panels.exceptions import TSVIncorrectFormat
from panels.exceptions import UsersDoNotExist
from panels.exceptions import GenesDoNotExist
from panels.tasks import background_copy_reviews


class UploadGenesForm(forms.Form):
    gene_list = forms.FileField(label='Select a file', required=True)

    def process_file(self, **kwargs):
        gene_list = UploadedGeneList.objects.create(gene_list=self.cleaned_data['gene_list'])
        gene_list.create_genes()


class UploadPanelsForm(forms.Form):
    panel_list = forms.FileField(label='Select a file', required=True)

    def process_file(self, **kwargs):
        message = None
        panel_list = UploadedPanelList.objects.create(panel_list=self.cleaned_data['panel_list'])
        try:
            return panel_list.process_file(kwargs.pop('user'))
        except GeneDoesNotExist as e:
            message = 'Line: {} has a wrong gene, please check it and try again.'.format(e)
        except UserDoesNotExist as e:
            message = 'Line: {} has a wrong username, please check it and try again.'.format(e)
        except UsersDoNotExist as e:
            message = "Can't find following users: {}, please check it and try again.".format(e)
        except GenesDoNotExist as e:
            message = "Can't find following genes: {}, please check it and try again.".format(e)
        except TSVIncorrectFormat as e:
            message = "Line: {} is not properly formatted, please check it and try again.".format(e)

        if message:
            raise forms.ValidationError(message)


class UploadReviewsForm(forms.Form):
    review_list = forms.FileField(label='Select a file', required=True)

    def process_file(self, **kwargs):
        message = None
        review_list = UploadedReviewsList.objects.create(reviews=self.cleaned_data['review_list'])
        try:
            return review_list.process_file(kwargs.pop('user'))
        except GeneDoesNotExist as e:
            message = 'Line: {} has a wrong gene, please check it and try again.'.format(e)
        except UserDoesNotExist as e:
            message = 'Line: {} has a wrong username, please check it and try again.'.format(e)
        except UsersDoNotExist as e:
            message = "Can't find following users: {}, please check it and try again.".format(e)
        except GenesDoNotExist as e:
            message = "Can't find following genes: {}, please check it and try again.".format(e)
        except TSVIncorrectFormat as e:
            message = "Line: {} is not properly formatted, please check it and try again.".format(e)
        if message:
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

    def copy_reviews(self, user, gene_symbols, panel_from, panel_to):
        if len(panel_to.current_genes) > 1000 or len(panel_from.current_genes) > 1000:
            background_copy_reviews.delay(user, gene_symbols, panel_from.pk, panel_to.pk)
            return ProcessingRunCode.PROCESS_BACKGROUND, 0
        else:
            with transaction.atomic():
                panel_to = panel_to.increment_version()
                return ProcessingRunCode.PROCESSED, panel_to.copy_gene_reviews_from(gene_symbols, panel_from)
        return 0, 0
