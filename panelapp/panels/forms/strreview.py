from collections import OrderedDict
from django import forms
from django.contrib.postgres.forms import SimpleArrayField
from panels.models import Evaluation


class STRReviewForm(forms.ModelForm):
    class Meta:
        model = Evaluation
        exclude = (
            'user',
            'version',
            'comments',
            'mode_of_pathogenicity'
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
        self.str_item = kwargs.pop('str_item')
        super().__init__(*args, **kwargs)

        original_fields = self.fields

        self.fields = OrderedDict()
        self.fields['rating'] = original_fields.get('rating')
        self.fields['moi'] = original_fields.get('moi')
        self.fields['publications'] = original_fields.get('publications')
        self.fields['phenotypes'] = original_fields.get('phenotypes')
        self.fields['current_diagnostic'] = original_fields.get('current_diagnostic')
        self.fields['clinically_relevant'] = original_fields.get('clinically_relevant')
        self.fields['comments'] = original_fields.get('comments')

    def save(self, *args, **kwargs):
        evaluation_data = self.cleaned_data
        evaluation_data['comment'] = evaluation_data.pop('comments')
        panel = self.str_item.panel
        ev = panel.get_str(self.str_item.name).update_evaluation(self.request.user, evaluation_data)
        panel.update_saved_stats()
        return ev
