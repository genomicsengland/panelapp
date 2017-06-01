from collections import OrderedDict
from django import forms
from django.contrib.postgres.forms import SimpleArrayField
from dal_select2.widgets import ModelSelect2
from dal_select2.widgets import Select2Multiple
from dal_select2.widgets import ModelSelect2Multiple
from panelapp.forms import Select2ListMultipleChoiceField
from .models import Comment
from .models import Tag
from .models import Gene
from .models import Evidence
from .models import Evaluation
from .models import Level4Title
from .models import GenePanel
from .models import GenePanelSnapshot
from .models import GenePanelEntrySnapshot
from .models import TrackRecord
from .models import UploadedGeneList


class PanelForm(forms.ModelForm):
    level2 = forms.CharField()
    level3 = forms.CharField()
    level4 = forms.CharField()
    description = forms.CharField(widget=forms.Textarea)
    omim = forms.CharField()
    orphanet = forms.CharField()
    hpo = forms.CharField()

    class Meta:
        model = GenePanelSnapshot
        fields = ('old_panels',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        original_fields = self.fields

        self.fields = OrderedDict()
        self.fields['level2'] = original_fields.get('level2')
        self.fields['level3'] = original_fields.get('level3')
        self.fields['level4'] = original_fields.get('level4')
        self.fields['description'] = original_fields.get('description')
        self.fields['omim'] = original_fields.get('omim')
        self.fields['orphanet'] = original_fields.get('orphanet')
        self.fields['hpo'] = original_fields.get('hpo')
        self.fields['old_panels'] = original_fields.get('old_panels')

    def clean_omim(self):
        return self._clean_array(self.cleaned_data['omim'])

    def clean_orphanet(self):
        return self._clean_array(self.cleaned_data['orphanet'])

    def clean_hpo(self):
        return self._clean_array(self.cleaned_data['hpo'])

    def save(self, *args, **kwargs):
        new_level4 = Level4Title(
            level2title=self.cleaned_data['level2'].strip(),
            level3title=self.cleaned_data['level3'].strip(),
            name=self.cleaned_data['level4'].strip(),
            description=self.cleaned_data['description'].strip(),
            omim=self.cleaned_data['omim'],
            hpo=self.cleaned_data['hpo'],
            orphanet=self.cleaned_data['orphanet']
        )

        if self.instance.id:
            panel = self.instance.panel
            level4title = self.instance.level4title

            data_changed = False
            if level4title.dict_tr() != new_level4.dict_tr():
                data_changed = True
                new_level4.save()
                self.instance.level4title = new_level4
                self.instance.panel.name = new_level4.name

            if 'old_panels' in self.changed_data:
                data_changed = True
                self.instance.old_panels = self.cleaned_data['old_panels']

            if data_changed:
                self.instance.panel.save()
                self.instance.increment_version()

        else:
            panel = GenePanel.objects.create(name=self.cleaned_data['level4'].strip())
            new_level4.save()

            self.instance.panel = panel
            self.instance.level4title = new_level4
            self.instance.old_panels = self.cleaned_data['old_panels']
            self.instance.save()

    def _clean_array(self, data, separator=","):
        return [x.strip() for x in data.split(separator) if x.strip()]


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


class PromotePanelForm(forms.ModelForm):
    """
    This form increments a major version and saves new version comment
    """
    version_comment = forms.CharField(label="Comment about this new version", widget=forms.Textarea)

    class Meta:
        model = GenePanelSnapshot
        fields = ('version_comment',)

    def save(self, *args, commit=True, **kwargs):
        self.instance.increment_version(major=True)
        return self.instance


class PanelAddGeneForm(forms.ModelForm):
    """
    The goal for this form is to add a Gene to a Panel.

    How this works:

    This form actually contains data for multiple models: GenePanelEntrySnapshot, Evidence, Evaluation.
    Some of this data is duplicated, and it's not clear if it needs to stay this way or should be refactored
    and moved to the models where it belongs. I.e. GenePanelEntrySnapshot has moi, mop, comments, etc. It's
    not clear if we need to keep it here, or move it to Evaluation model since it has the same values.

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
        queryset=Gene.objects.all(),
        widget=ModelSelect2(url="autocomplete-gene")
    )
    source = Select2ListMultipleChoiceField(
        choice_list=Evidence.ALL_SOURCES,
        widget=Select2Multiple(url="autocomplete-source")
    )
    tags = forms.ModelMultipleChoiceField(
        queryset=Tag.objects.all(),
        widget=ModelSelect2Multiple(url="autocomplete-tags"),
        required=False
    )

    publications = SimpleArrayField(forms.CharField(max_length=255), delimiter=";")
    phenotypes = SimpleArrayField(forms.CharField(max_length=255), delimiter=";")

    rating = forms.ChoiceField(choices=[('', 'Provide rating')] + Evaluation.RATINGS)
    current_diagnostic = forms.BooleanField()
    comments = forms.CharField(widget=forms.Textarea)

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
        self.fields['source'] = original_fields.get('source')
        self.fields['mode_of_pathogenicity'] = original_fields.get('mode_of_pathogenicity')
        self.fields['moi'] = original_fields.get('moi')
        self.fields['penetrance'] = original_fields.get('penetrance')
        self.fields['publications'] = original_fields.get('publications')
        self.fields['phenotypes'] = original_fields.get('phenotypes')
        self.fields['tags'] = original_fields.get('tags')
        self.fields['rating'] = original_fields.get('rating')
        self.fields['current_diagnostic'] = original_fields.get('current_diagnostic')
        self.fields['comments'] = original_fields.get('comments')

    def clean_gene_symbol(self):
        gene_symbol = self.cleaned_data['gene'].gene_symbol
        if not self.instance.pk and self.panel.has_gene(gene_symbol):
            raise forms.ValidationError(
                "Gene has already been added to the panel",
                code='gene_exists_in_panel',
            )
        return gene_symbol

    def import_gene(self, symbol_name):
        return Gene.objects.get(gene_symbol=symbol_name).dict_tr()

    def save(self, *args, **kwargs):
        flagged = False if self.request.user.reviewer.is_GEL() else True
        gene = self.cleaned_data['gene']

        # increment minor version in the panel
        self.panel.increment_version()

        gpe = GenePanelEntrySnapshot.objects.create(
            panel=self.panel,
            gene=self.import_gene(gene.gene_symbol),
            gene_core=gene,
            moi=self.cleaned_data['moi'],
            penetrance=self.cleaned_data['penetrance'],
            publications=self.cleaned_data['publications'],
            phenotypes=self.cleaned_data['phenotypes'],
            flagged=flagged,
            mode_of_pathogenicity=self.cleaned_data['mode_of_pathogenicity'],
            saved_gel_status=0
        )

        comment = Comment.objects.create(
            user=self.request.user,
            comment=self.cleaned_data['comments']
        )
        gpe.comments.add(comment)

        for source in self.cleaned_data['source']:
            evidence = Evidence.objects.create(
                rating=5,
                reviewer=self.request.user.reviewer,
                name=source.strip()
            )
            gpe.evidence.add(evidence)

        track_created = TrackRecord.objects.create(
            gel_status=gpe.evidence_status(),
            curator_status=0,
            user=self.request.user,
            issue_type=TrackRecord.ISSUE_TYPES.Created,
            issue_description="{} was created by {}".format(gene.gene_symbol, self.request.user.get_full_name())
        )
        gpe.track.add(track_created)

        description = "{} was added to {} panel. Sources: {}".format(
            gene.gene_symbol,
            self.panel.panel.name,
            ",".join(self.cleaned_data['source'])
        )
        track_sources = TrackRecord.objects.create(
            gel_status=gpe.evidence_status(),
            curator_status=0,
            user=self.request.user,
            issue_type=TrackRecord.ISSUE_TYPES.NewSource,
            issue_description=description
        )
        gpe.track.add(track_sources)
        gpe.evidence_status(update=True)
        return gpe
