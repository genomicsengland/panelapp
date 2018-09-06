from collections import OrderedDict
from django import forms
from django.contrib.postgres.forms import SimpleArrayField
from panels.models import Evaluation


class RegionReviewForm(forms.ModelForm):
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
    clinically_relevant = forms.BooleanField(
        label="Interruptions are clinically relevant",
        required=False,
        help_text="Interruptions in the repeated sequence are reported as part of standard diagnostic practice"
    )
    comments = forms.CharField(widget=forms.Textarea, required=False)

    def __init__(self, *args, **kwargs):
        self.panel = kwargs.pop('panel')
        self.request = kwargs.pop('request')
        self.region = kwargs.pop('region')
        super().__init__(*args, **kwargs)

        original_fields = self.fields

        self.fields = OrderedDict()
        self.fields['rating'] = original_fields.get('rating')
        self.fields['moi'] = original_fields.get('moi')
        self.fields['publications'] = original_fields.get('publications')
        self.fields['phenotypes'] = original_fields.get('phenotypes')
        self.fields['current_diagnostic'] = original_fields.get('current_diagnostic')
        self.fields['comments'] = original_fields.get('comments')

    def save(self, *args, **kwargs):
        evaluation_data = self.cleaned_data
        evaluation_data['comment'] = evaluation_data.pop('comments')
        panel = self.region.panel
        ev = panel.get_region(self.region.name).update_evaluation(self.request.user, evaluation_data)
        panel.update_saved_stats()
        return ev
