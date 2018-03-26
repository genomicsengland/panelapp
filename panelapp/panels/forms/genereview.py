from collections import OrderedDict
from django import forms
from django.contrib.postgres.forms import SimpleArrayField
from panels.models import Evaluation


class GeneReviewForm(forms.ModelForm):
    class Meta:
        model = Evaluation
        exclude = (
            'user',
            'version',
            'comments',
            'clinically_relevant'
        )

    publications = SimpleArrayField(
        forms.CharField(),
        label="Publications (PMID: 1234;4321)",
        delimiter=";",
        required=False
    )
    phenotypes = SimpleArrayField(
        forms.CharField(),
        label="Phenotypes (separate using a semi-colon - ;)",
        delimiter=";",
        required=False
    )

    rating = forms.ChoiceField(choices=[('', 'Provide rating')] + Evaluation.RATINGS, required=False)
    current_diagnostic = forms.BooleanField(required=False)
    comments = forms.CharField(widget=forms.Textarea, required=False)

    def __init__(self, *args, **kwargs):
        self.panel = kwargs.pop('panel')
        self.request = kwargs.pop('request')
        self.gene = kwargs.pop('gene')
        super().__init__(*args, **kwargs)

        original_fields = self.fields

        self.fields = OrderedDict()
        self.fields['rating'] = original_fields.get('rating')
        self.fields['moi'] = original_fields.get('moi')
        self.fields['mode_of_pathogenicity'] = original_fields.get('mode_of_pathogenicity')
        self.fields['publications'] = original_fields.get('publications')
        self.fields['phenotypes'] = original_fields.get('phenotypes')
        self.fields['current_diagnostic'] = original_fields.get('current_diagnostic')
        self.fields['comments'] = original_fields.get('comments')

    def save(self, *args, **kwargs):
        evaluation_data = self.cleaned_data
        evaluation_data['comment'] = evaluation_data.pop('comments')
        panel = self.gene.panel
        ev = panel.get_gene(self.gene.gene.get('gene_symbol')).update_evaluation(self.request.user, evaluation_data)
        panel.update_saved_stats()
        return ev
