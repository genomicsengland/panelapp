"""Contains a form which is used to add/edit a gene in a panel."""

from collections import OrderedDict
from django import forms
from django.contrib.postgres.forms import SimpleArrayField
from dal_select2.widgets import ModelSelect2
from dal_select2.widgets import Select2Multiple
from dal_select2.widgets import ModelSelect2Multiple
from panelapp.forms import Select2ListMultipleChoiceField
from panels.models import Tag
from panels.models import Gene
from panels.models import Evidence
from panels.models import Evaluation
from panels.models import GenePanelEntrySnapshot
from panels.models import GenePanel


class PanelGeneForm(forms.ModelForm):
    """
    The goal for this form is to add a Gene to a Panel.

    How this works:

    This form actually contains data for multiple models: GenePanelEntrySnapshot,
    Evidence, Evaluation. Some of this data is duplicated, and it's not clear if
    it needs to stay this way or should be refactored and moved to the models where
    it belongs. I.e. GenePanelEntrySnapshot has moi, mop, comments, etc. It's
    not clear if we need to keep it here, or move it to Evaluation model since
    it has the same values.

    When user clicks save we:

    1) Get Gene data and add it to the JSONField
    2) Create Comment
    3) Create Evaluation
    4) Create Evidence
    5) Create new copy of GenePanelSnapshot, increment minor version
    6) Create new GenePanelEntrySnapshot with a link to the new GenePanelSnapshot
    """

    gene = forms.ModelChoiceField(
        label="Gene symbol",
        queryset=Gene.objects.filter(active=True),
        widget=ModelSelect2(
            url="autocomplete-gene",
            attrs={'data-minimum-input-length': 1}
        )
    )

    gene_name = forms.CharField()

    source = Select2ListMultipleChoiceField(
        choice_list=Evidence.ALL_SOURCES, required=False,
        widget=Select2Multiple(url="autocomplete-source")
    )
    tags = forms.ModelMultipleChoiceField(
        queryset=Tag.objects.all(), required=False,
        widget=ModelSelect2Multiple(url="autocomplete-tags")
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

    rating = forms.ChoiceField(
        choices=[('', 'Provide rating')] + Evaluation.RATINGS,
        required=False
    )
    current_diagnostic = forms.BooleanField(required=False)
    comments = forms.CharField(widget=forms.Textarea, required=False)

    class Meta:
        model = GenePanelEntrySnapshot
        fields = (
            'mode_of_pathogenicity',
            'moi',
            'penetrance',
            'publications',
            'phenotypes',
        )

    def __init__(self, *args, **kwargs):
        self.panel = kwargs.pop('panel')
        self.request = kwargs.pop('request')
        super().__init__(*args, **kwargs)

        original_fields = self.fields

        self.fields = OrderedDict()
        self.fields['gene'] = original_fields.get('gene')
        if self.instance.pk:
            self.fields['gene_name'] = original_fields.get('gene_name')
        self.fields['source'] = original_fields.get('source')
        self.fields['mode_of_pathogenicity'] = original_fields.get('mode_of_pathogenicity')
        self.fields['moi'] = original_fields.get('moi')
        self.fields['moi'].required = False
        self.fields['penetrance'] = original_fields.get('penetrance')
        self.fields['publications'] = original_fields.get('publications')
        self.fields['phenotypes'] = original_fields.get('phenotypes')
        if self.request.user.is_authenticated and self.request.user.reviewer.is_GEL():
            self.fields['tags'] = original_fields.get('tags')
        if not self.instance.pk:
            self.fields['rating'] = original_fields.get('rating')
            self.fields['current_diagnostic'] = original_fields.get('current_diagnostic')
            self.fields['comments'] = original_fields.get('comments')

    def clean_source(self):
        if len(self.cleaned_data['source']) < 1:
            raise forms.ValidationError('Please select a source')
        return self.cleaned_data['source']

    def clean_moi(self):
        if not self.cleaned_data['moi']:
            raise forms.ValidationError('Please select a mode of inheritance')
        return self.cleaned_data['moi']

    def clean_gene(self):
        "Check if gene exists in a panel if we add a new gene or change the gene"

        gene_symbol = self.cleaned_data['gene'].gene_symbol
        if not self.instance.pk and self.panel.has_gene(gene_symbol):
            raise forms.ValidationError(
                "Gene has already been added to the panel",
                code='gene_exists_in_panel',
            )
        elif self.instance.pk and 'gene' in self.changed_data \
                and gene_symbol != self.instance.gene.get('gene_symbol')\
                and self.panel.has_gene(gene_symbol):
            raise forms.ValidationError(
                "Gene has already been added to the panel",
                code='gene_exists_in_panel',
            )
        if not self.cleaned_data.get('gene_name'):
            self.cleaned_data['gene_name'] = self.cleaned_data['gene'].gene_name

        return self.cleaned_data['gene']

    def save(self, *args, **kwargs):
        "Don't save the original panel as we need to increment version first"
        return False

    def save_gene(self, *args, **kwargs):
        "Saves the gene, increments version and returns the gene back"

        gene_data = self.cleaned_data
        gene_data['sources'] = gene_data.pop('source')

        if gene_data.get('comments'):
            gene_data['comment'] = gene_data.pop('comments')

        if self.initial:
            initial_gene_symbol = self.initial['gene_json'].get('gene_symbol')
        else:
            initial_gene_symbol = None

        new_gene_symbol = gene_data.get('gene').gene_symbol

        if self.initial and self.panel.has_gene(initial_gene_symbol):
            self.panel = self.panel.increment_version()
            self.panel = GenePanel.objects.get(pk=self.panel.panel.pk).active_panel
            self.panel.update_gene(
                self.request.user,
                initial_gene_symbol,
                gene_data
            )
            self.panel = GenePanel.objects.get(pk=self.panel.panel.pk).active_panel
            self.panel.create_backup()
            return self.panel.get_gene(new_gene_symbol)
        else:
            increment_version = self.request.user.is_authenticated and self.request.user.reviewer.is_GEL()
            gene = self.panel.add_gene(
                self.request.user,
                new_gene_symbol,
                gene_data,
                increment_version
            )
            self.panel = GenePanel.objects.get(pk=self.panel.panel.pk).active_panel
            self.panel.create_backup()
            self.panel.update_saved_stats()
            return gene
