from collections import OrderedDict
from django import forms
from django.contrib.postgres.forms import SimpleArrayField
from dal_select2.widgets import ModelSelect2Multiple
from panels.models import Tag
from panels.models import GenePanel
from panels.models import GenePanelEntrySnapshot


class UpdateGeneTagsForm(forms.ModelForm):
    class Meta:
        model = GenePanelEntrySnapshot
        fields = ('tags',)

    tags = forms.ModelMultipleChoiceField(
        queryset=Tag.objects.all(),
        widget=ModelSelect2Multiple(url="autocomplete-tags"),
        required=False
    )

    def save(self, *args, **kwargs):
        if 'tags' in self.changed_data:
            self.instance.update_tags(kwargs['user'], self.cleaned_data['tags'])


class UpdateGeneMOPForm(forms.ModelForm):
    comment = forms.CharField(required=False, widget=forms.Textarea)

    class Meta:
        model = GenePanelEntrySnapshot
        fields = ('mode_of_pathogenicity',)

    def save(self, *args, **kwargs):
        mop = self.cleaned_data['mode_of_pathogenicity']
        comment = self.cleaned_data['comment']
        user = kwargs.pop('user')
        self.instance.panel.increment_version()
        self.instance = GenePanel.objects.get(pk=self.instance.panel.panel.pk)\
            .active_panel.get_gene(self.instance.gene['gene_symbol'])
        self.instance.update_pathogenicity(mop, user, comment)
        self.instance.panel.update_saved_stats()


class UpdateGeneMOIForm(forms.ModelForm):
    comment = forms.CharField(required=False, widget=forms.Textarea)

    class Meta:
        model = GenePanelEntrySnapshot
        fields = ('moi',)

    def save(self, *args, **kwargs):
        moi = self.cleaned_data['moi']
        comment = self.cleaned_data['comment']
        user = kwargs.pop('user')
        self.instance.panel.increment_version()
        self.instance = GenePanel.objects.get(pk=self.instance.panel.panel.pk)\
            .active_panel.get_gene(self.instance.gene['gene_symbol'])
        self.instance.update_moi(moi, user, comment)
        self.instance.panel.update_saved_stats()


class UpdateGenePhenotypesForm(forms.ModelForm):
    comment = forms.CharField(required=False, widget=forms.Textarea)
    phenotypes = SimpleArrayField(
        forms.CharField(max_length=255),
        label="Phenotypes (separate using a semi-colon - ;)",
        delimiter=";"
    )

    class Meta:
        model = GenePanelEntrySnapshot
        fields = ('phenotypes',)

    def save(self, *args, **kwargs):
        phenotypes = self.cleaned_data['phenotypes']
        comment = self.cleaned_data['comment']
        user = kwargs.pop('user')
        self.instance.panel.increment_version()
        self.instance = GenePanel.objects.get(pk=self.instance.panel.panel.pk)\
            .active_panel.get_gene(self.instance.gene['gene_symbol'])
        self.instance.update_phenotypes(phenotypes, user, comment)
        self.instance.panel.update_saved_stats()


class UpdateGenePublicationsForm(forms.ModelForm):
    comment = forms.CharField(required=False, widget=forms.Textarea)

    publications = SimpleArrayField(
        forms.CharField(max_length=255),
        label="Publications (separate using a semi-colon - ;)",
        delimiter=";"
    )

    class Meta:
        model = GenePanelEntrySnapshot
        fields = ('publications',)

    def save(self, *args, **kwargs):
        publications = self.cleaned_data['publications']
        comment = self.cleaned_data['comment']
        user = kwargs.pop('user')
        self.instance.panel.increment_version()
        self.instance = GenePanel.objects.get(pk=self.instance.panel.panel.pk)\
            .active_panel.get_gene(self.instance.gene['gene_symbol'])
        self.instance.update_publications(publications, user, comment)
        self.instance.panel.update_saved_stats()


class UpdateGeneRatingForm(forms.ModelForm):
    comment = forms.CharField(required=False, widget=forms.Textarea)
    status = forms.ChoiceField(choices=GenePanelEntrySnapshot.GEL_STATUS)

    class Meta:
        model = GenePanelEntrySnapshot
        fields = ('saved_gel_status',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        original_fields = self.fields
        self.fields = OrderedDict()
        self.fields['status'] = original_fields['status']
        self.fields['status'].initial = self.instance.saved_gel_status
        self.fields['comment'] = original_fields['comment']

    def save(self, *args, **kwargs):
        status = self.cleaned_data['status']
        user = kwargs.pop('user')
        self.instance.panel.increment_version()
        self.instance = GenePanel.objects.get(pk=self.instance.panel.panel.pk)\
            .active_panel.get_gene(self.instance.gene['gene_symbol'])
        self.instance.update_rating(status, user, self.cleaned_data['comment'])
        self.instance.panel.update_saved_stats()
