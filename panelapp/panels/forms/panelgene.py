from collections import OrderedDict
from django import forms
from django.contrib.postgres.forms import SimpleArrayField
from dal_select2.widgets import ModelSelect2
from dal_select2.widgets import Select2Multiple
from dal_select2.widgets import ModelSelect2Multiple
from panelapp.forms import Select2ListMultipleChoiceField
from panels.models import Comment
from panels.models import Tag
from panels.models import Gene
from panels.models import Evidence
from panels.models import Evaluation
from panels.models import GenePanelEntrySnapshot
from panels.models import TrackRecord


class PanelGeneForm(forms.ModelForm):
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

    gene_name = forms.CharField()

    source = Select2ListMultipleChoiceField(
        choice_list=Evidence.ALL_SOURCES,
        widget=Select2Multiple(url="autocomplete-source")
    )
    tags = forms.ModelMultipleChoiceField(
        queryset=Tag.objects.all(),
        widget=ModelSelect2Multiple(url="autocomplete-tags"),
        required=False
    )

    publications = SimpleArrayField(
        forms.CharField(max_length=255),
        label="Publications (PMID: 1234;4321)",
        delimiter=";"
    )
    phenotypes = SimpleArrayField(
        forms.CharField(max_length=255),
        label="Phenotypes (separate using a semi-colon - ;)",
        delimiter=";"
    )

    rating = forms.ChoiceField(choices=[('', 'Provide rating')] + Evaluation.RATINGS)
    current_diagnostic = forms.BooleanField(required=False)
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
        if self.instance.pk:
            self.fields['gene_name'] = original_fields.get('gene_name')
        self.fields['source'] = original_fields.get('source')
        self.fields['mode_of_pathogenicity'] = original_fields.get('mode_of_pathogenicity')
        self.fields['moi'] = original_fields.get('moi')
        self.fields['penetrance'] = original_fields.get('penetrance')
        self.fields['publications'] = original_fields.get('publications')
        self.fields['phenotypes'] = original_fields.get('phenotypes')
        self.fields['tags'] = original_fields.get('tags')
        if not self.instance.pk:
            self.fields['rating'] = original_fields.get('rating')
            self.fields['current_diagnostic'] = original_fields.get('current_diagnostic')
            self.fields['comments'] = original_fields.get('comments')

    def clean_gene(self):
        gene_symbol = self.cleaned_data['gene'].gene_symbol
        if not self.instance.pk and self.panel.has_gene(gene_symbol):
            raise forms.ValidationError(
                "Gene has already been added to the panel",
                code='gene_exists_in_panel',
            )
        elif self.instance.pk and 'gene' in self.changed_data and self.panel.has_gene(gene_symbol):
            raise forms.ValidationError(
                "Gene has already been added to the panel",
                code='gene_exists_in_panel',
            )
        if not self.cleaned_data.get('gene_name'):
            self.cleaned_data['gene_name'] = self.cleaned_data['gene'].gene_name

        return self.cleaned_data['gene']

    def import_gene(self, symbol_name):
        return Gene.objects.get(gene_symbol=symbol_name).dict_tr()

    def save(self, *args, **kwargs):
        # increment minor version in the panel
        self.panel.increment_version()

        gene = self.cleaned_data['gene']
        gene_data = self.import_gene(gene.gene_symbol)

        if not self.instance.pk:
            self.instance = GenePanelEntrySnapshot(
                gene=gene_data,
                panel=self.panel,
                gene_core=gene,
                moi=self.cleaned_data['moi'],
                penetrance=self.cleaned_data['penetrance'],
                publications=self.cleaned_data['publications'],
                phenotypes=self.cleaned_data['phenotypes'],
                mode_of_pathogenicity=self.cleaned_data['mode_of_pathogenicity'],
                saved_gel_status=0
            )

            self.instance.flagged = False if self.request.user.reviewer.is_GEL() else True
            self.instance.save()

            comment = Comment.objects.create(
                user=self.request.user,
                comment=self.cleaned_data['comments']
            )
            self.instance.comments.add(comment)

            for source in self.cleaned_data['source']:
                evidence = Evidence.objects.create(
                    rating=5,
                    reviewer=self.request.user.reviewer,
                    name=source.strip()
                )
                self.instance.evidence.add(evidence)

            evidence_status = self.instance.evidence_status()
            track_created = TrackRecord.objects.create(
                gel_status=evidence_status,
                curator_status=0,
                user=self.request.user,
                issue_type=TrackRecord.ISSUE_TYPES.Created,
                issue_description="{} was created by {}".format(gene.gene_symbol, self.request.user.get_full_name())
            )
            self.instance.track.add(track_created)

            description = "{} was added to {} panel. Sources: {}".format(
                gene.gene_symbol,
                self.panel.panel.name,
                ",".join(self.cleaned_data['source'])
            )
            track_sources = TrackRecord.objects.create(
                gel_status=evidence_status,
                curator_status=0,
                user=self.request.user,
                issue_type=TrackRecord.ISSUE_TYPES.NewSource,
                issue_description=description
            )
            self.instance.track.add(track_sources)

            # Add initial evaluation here
            evaluation = Evaluation.objects.create(
                user=self.request.user,
                rating=self.cleaned_data['rating'],
                mode_of_pathogenicity=self.cleaned_data['mode_of_pathogenicity'],
                phenotypes=self.cleaned_data['phenotypes'],
                publications=self.cleaned_data['publications'],
                moi=self.cleaned_data['moi'],
                current_diagnostic=self.cleaned_data['current_diagnostic'],
                version=self.panel.version
            )
            evaluation.comments.add(comment)
            self.instance.evaluation.add(evaluation)

            self.instance.evidence_status(update=True)
        else:
            gene_data['gene_name'] = self.cleaned_data['gene_name']
            evidence_status = self.instance.evidence_status()

            self.instance.pk = None
            self.instance.panel = self.panel
            self.instance.mode_of_pathogenicity = self.cleaned_data['mode_of_pathogenicity']
            self.instance.penetrance = self.cleaned_data['penetrance']
            self.instance.publications = self.cleaned_data['publications']
            self.instance.save()

            new_sources = []
            for source in self.cleaned_data['source']:
                prev_sources = [s.name for s in self.instance.evidence.all()]
                for source in self.cleaned_data['source']:
                    if source not in prev_sources:
                        new_sources.append(source)
                        evidence = Evidence.objects.create(
                            name=source,
                            rating=5,
                            comment="",
                            reviewer=self.request.user.reviewer
                        )
                        self.instance.evidence.add(evidence)
            if len(new_sources) > 0:
                evidence_status = self.instance.evidence_status()
                description = "New sources were added to {}. Sources: {}".format(
                    gene.gene_symbol,
                    ",".join(new_sources)
                )
                track_sources = TrackRecord.objects.create(
                    gel_status=evidence_status,
                    curator_status=0,
                    user=self.request.user,
                    issue_type=TrackRecord.ISSUE_TYPES.NewSource,
                    issue_description=description
                )
                self.instance.track.add(track_sources)

            if 'phenotypes' in self.changed_data:
                self.instance.phenotypes = self.cleaned_data['phenotypes']
                description = "Phenotypes for gene {} were set to {}".format(
                    gene.gene_symbol,
                    ";".join(self.instance.phenotypes)
                )
                track_phenotypes = TrackRecord.objects.create(
                    gel_status=evidence_status,
                    curator_status=0,
                    user=self.request.user,
                    issue_type=TrackRecord.ISSUE_TYPES.SetPhenotypes,
                    issue_description=description
                )
                self.instance.track.add(track_phenotypes)

            if 'moi' in self.changed_data:
                self.instance.moi = self.cleaned_data['moi']
                description = "Model of inheritance for gene {} were set to {}".format(
                    gene.gene_symbol,
                    self.instance.moi
                )
                track_moi = TrackRecord.objects.create(
                    gel_status=evidence_status,
                    curator_status=0,
                    user=self.request.user,
                    issue_type=TrackRecord.ISSUE_TYPES.SetModelofInheritance,
                    issue_description=description
                )
                self.instance.track.add(track_moi)

            if self.instance.gene_core != gene:
                old_gene_symbol = self.instance.gene_core.gene_symbol
                description = "{} was changed to {}".format(old_gene_symbol, gene.gene_symbol)
                track_gene = TrackRecord.objects.create(
                    gel_status=evidence_status,
                    curator_status=0,
                    user=self.request.user,
                    issue_type=TrackRecord.ISSUE_TYPES.ChangedGeneName,
                    issue_description=description
                )
                self.instance.track.add(track_gene)
                self.instance.gene_core = gene
                self.instance.gene = gene_data
                self.instance.save()
                self.panel.delete_gene(old_gene_symbol, increment=False)
            elif self.instance.gene.get('gene_name') != self.cleaned_data['gene_name']:
                self.instance.gene['gene_name'] = self.cleaned_data['gene_name']
                self.instance.save()

        return self.instance