from collections import OrderedDict
from django import forms
from django.contrib.postgres.forms import SimpleArrayField
from panels.models import Comment
from panels.models import Evaluation


class GeneReviewForm(forms.ModelForm):
    class Meta:
        model = Evaluation
        exclude = (
            'user',
            'version',
            'comments',
        )

    publications = SimpleArrayField(
        forms.CharField(max_length=255),
        label="Publications (PMID: 1234;4321)",
        delimiter=";",
        required=False
    )
    phenotypes = SimpleArrayField(
        forms.CharField(max_length=255),
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
        try:
            # User has already added a valuation, we only update the values and add a comment
            evaluation = self.gene.evaluation.get(user=self.request.user)

            comment = None
            changed = False

            if self.cleaned_data['comments']:
                comment = Comment.objects.create(
                    user=self.request.user,
                    comment=self.cleaned_data['comments']
                )
                evaluation.comments.add(comment)

            mop = self.cleaned_data['mode_of_pathogenicity']
            if mop and evaluation.mode_of_pathogenicity != mop:
                changed = True
                evaluation.mode_of_pathogenicity = mop

            publications = self.cleaned_data['publications']
            if publications and evaluation.publications != publications:
                changed = True
                evaluation.publications = publications

            phenotypes = self.cleaned_data['phenotypes']
            if phenotypes and evaluation.phenotypes != phenotypes:
                changed = True
                evaluation.phenotypes = phenotypes

            moi = self.cleaned_data['moi']
            if moi and evaluation.moi != moi:
                changed = True
                evaluation.moi = moi

            current_diagnostic = self.cleaned_data['current_diagnostic']
            if moi and evaluation.current_diagnostic != current_diagnostic:
                changed = True
                evaluation.current_diagnostic = current_diagnostic

            evaluation.version = self.panel.version

            if changed:
                activity_text = "commented on {}".format(self.gene.gene.get('gene_symbol'))
                self.panel.add_activity(self.request.user, self.gene.gene.get('gene_symbol'), activity_text)
            elif comment:
                activity_text = "edited their review of {}".format(self.gene.gene.get('gene_symbol'))
                self.panel.add_activity(self.request.user, self.gene.gene.get('gene_symbol'), activity_text)

        except Evaluation.DoesNotExist:
            if self.cleaned_data['comments']:
                comment = Comment.objects.create(
                    user=self.request.user,
                    comment=self.cleaned_data['comments']
                )

            evaluation = Evaluation.objects.create(
                user=self.request.user,
                rating=self.cleaned_data['rating'],
                mode_of_pathogenicity=self.cleaned_data['mode_of_pathogenicity'],
                publications=self.cleaned_data['publications'],
                phenotypes=self.cleaned_data['phenotypes'],
                moi=self.cleaned_data['moi'],
                current_diagnostic=self.cleaned_data['current_diagnostic'],
                version=self.panel.version
            )
            self.gene.evaluation.add(evaluation)

            if self.cleaned_data['comments']:
                evaluation.comments.add(comment)
            if evaluation.is_comment_without_review():
                activity_text = "commented on {}".format(self.gene.gene.get('gene_symbol'))
                self.panel.add_activity(self.request.user, self.gene.gene.get('gene_symbol'), activity_text)
            else:
                activity_text = "reviewed {}".format(self.gene.gene.get('gene_symbol'))
                self.panel.add_activity(self.request.user, self.gene.gene.get('gene_symbol'), activity_text)

        return evaluation
