##
## Copyright (c) 2016-2019 Genomics England Ltd.
##
## This file is part of PanelApp
## (see https://panelapp.genomicsengland.co.uk).
##
## Licensed to the Apache Software Foundation (ASF) under one
## or more contributor license agreements.  See the NOTICE file
## distributed with this work for additional information
## regarding copyright ownership.  The ASF licenses this file
## to you under the Apache License, Version 2.0 (the
## "License"); you may not use this file except in compliance
## with the License.  You may obtain a copy of the License at
##
##   http://www.apache.org/licenses/LICENSE-2.0
##
## Unless required by applicable law or agreed to in writing,
## software distributed under the License is distributed on an
## "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
## KIND, either express or implied.  See the License for the
## specific language governing permissions and limitations
## under the License.
##
"""Contains a form which is used to add/edit a gene in a panel."""

from collections import OrderedDict
from django import forms
from django.contrib.postgres.forms import SimpleArrayField
from django.contrib.postgres.forms import IntegerRangeField
from dal_select2.widgets import ModelSelect2
from dal_select2.widgets import Select2Multiple
from dal_select2.widgets import ModelSelect2Multiple
from panelapp.forms import Select2ListMultipleChoiceField
from panels.models import Tag
from panels.models import Gene
from panels.models import Evidence
from panels.models import Evaluation
from panels.models import STR
from panels.models import GenePanel


class PanelSTRForm(forms.ModelForm):
    """
    The goal for this form is to add a STR to a Panel.

    How this works:

    This form actually contains data for multiple models: STR,
    Evidence, Evaluation. Some of this data is duplicated, and it's not clear if
    it needs to stay this way or should be refactored and moved to the models where
    it belongs. I.e. GenePanelEntrySnapshot has moi, comments, etc. It's
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
        required=False,
        queryset=Gene.objects.filter(active=True),
        widget=ModelSelect2(
            url="autocomplete-gene", attrs={"data-minimum-input-length": 1}
        ),
    )

    position_37 = IntegerRangeField(require_all_fields=True, required=False)
    position_38 = IntegerRangeField(require_all_fields=True, required=True)

    gene_name = forms.CharField(required=False)

    source = Select2ListMultipleChoiceField(
        choice_list=Evidence.ALL_SOURCES,
        required=False,
        widget=Select2Multiple(url="autocomplete-source"),
    )
    tags = forms.ModelMultipleChoiceField(
        queryset=Tag.objects.all(),
        required=False,
        widget=ModelSelect2Multiple(url="autocomplete-tags"),
    )

    publications = SimpleArrayField(
        forms.CharField(),
        label="Publications (PMID: 1234;4321)",
        delimiter=";",
        required=False,
    )
    phenotypes = SimpleArrayField(
        forms.CharField(),
        label="Phenotypes (separate using a semi-colon - ;)",
        delimiter=";",
        required=False,
    )

    rating = forms.ChoiceField(
        choices=[("", "Provide rating")] + Evaluation.RATINGS, required=False
    )
    current_diagnostic = forms.BooleanField(required=False)
    clinically_relevant = forms.BooleanField(
        label="Interruptions are clinically relevant",
        required=False,
        help_text="Interruptions in the repeated sequence are reported as part of standard diagnostic practice",
    )
    comments = forms.CharField(widget=forms.Textarea, required=False)

    class Meta:
        model = STR
        fields = (
            "name",
            "chromosome",
            "position_37",
            "position_38",
            "repeated_sequence",
            "normal_repeats",
            "pathogenic_repeats",
            "moi",
            "penetrance",
            "publications",
            "phenotypes",
        )

    def __init__(self, *args, **kwargs):
        self.panel = kwargs.pop("panel")
        self.request = kwargs.pop("request")
        super().__init__(*args, **kwargs)

        original_fields = self.fields

        self.fields = OrderedDict()
        self.fields["name"] = original_fields.get("name")
        self.fields["chromosome"] = original_fields.get("chromosome")
        self.fields["position_37"] = original_fields.get("position_37")
        self.fields["position_37"].widget.widgets[0].attrs = {
            "placeholder": "Position start (GRCh37)"
        }
        self.fields["position_37"].widget.widgets[1].attrs = {
            "placeholder": "Position end (GRCh37)"
        }
        self.fields["position_38"] = original_fields.get("position_38")
        self.fields["position_38"].widget.widgets[0].attrs = {
            "placeholder": "Position start (GRCh38)"
        }
        self.fields["position_38"].widget.widgets[1].attrs = {
            "placeholder": "Position end (GRCh38)"
        }
        self.fields["repeated_sequence"] = original_fields.get("repeated_sequence")
        self.fields["normal_repeats"] = original_fields.get("normal_repeats")
        self.fields["pathogenic_repeats"] = original_fields.get("pathogenic_repeats")
        self.fields["gene"] = original_fields.get("gene")
        if self.instance.pk:
            self.fields["gene_name"] = original_fields.get("gene_name")
        self.fields["source"] = original_fields.get("source")
        self.fields["moi"] = original_fields.get("moi")
        self.fields["moi"].required = False
        self.fields["penetrance"] = original_fields.get("penetrance")
        self.fields["publications"] = original_fields.get("publications")
        self.fields["phenotypes"] = original_fields.get("phenotypes")
        if self.request.user.is_authenticated and self.request.user.reviewer.is_GEL():
            self.fields["tags"] = original_fields.get("tags")
        if not self.instance.pk:
            self.fields["rating"] = original_fields.get("rating")
            self.fields["current_diagnostic"] = original_fields.get(
                "current_diagnostic"
            )
            if self.instance.is_str():
                self.fields["clinically_relevant"] = original_fields.get(
                    "clinically_relevant"
                )
            self.fields["comments"] = original_fields.get("comments")

    def clean_source(self):
        if len(self.cleaned_data["source"]) < 1:
            raise forms.ValidationError("Please select a source")
        return self.cleaned_data["source"]

    def clean_moi(self):
        if not self.cleaned_data["moi"]:
            raise forms.ValidationError("Please select a mode of inheritance")
        return self.cleaned_data["moi"]

    def clean_repeated_sequence(self):
        if (
            len(
                set(self.cleaned_data["repeated_sequence"]).difference(
                    {"A", "T", "C", "G", "N"}
                )
            )
            > 0
        ):
            raise forms.ValidationError(
                "Repeated sequence contains incorrect nucleotides"
            )
        return self.cleaned_data["repeated_sequence"]

    def clean_name(self):
        """Check if gene exists in a panel if we add a new gene or change the gene"""

        name = self.cleaned_data["name"]
        if not self.instance.pk and self.panel.has_str(name):
            raise forms.ValidationError(
                "STR has already been added to the panel", code="str_exists_in_panel"
            )
        elif (
            self.instance.pk
            and "name" in self.changed_data
            and name != self.instance.name
            and self.panel.has_str(name)
        ):
            raise forms.ValidationError(
                "STR has already been added to the panel", code="str_exists_in_panel"
            )
        if not self.cleaned_data.get("name"):
            self.cleaned_data["name"] = self.cleaned_data["name"]

        return self.cleaned_data["name"]

    def save(self, *args, **kwargs):
        """Don't save the original panel as we need to increment version first"""
        return False

    def save_str(self, *args, **kwargs):
        """Saves the gene, increments version and returns the gene back"""

        str_data = self.cleaned_data
        str_data["sources"] = str_data.pop("source")

        if str_data.get("comments"):
            str_data["comment"] = str_data.pop("comments")

        if self.initial:
            initial_name = self.initial["name"]
        else:
            initial_name = None

        new_str_name = str_data["name"]

        if self.initial and self.panel.has_str(initial_name):
            self.panel = self.panel.increment_version()
            self.panel = GenePanel.objects.get(pk=self.panel.panel.pk).active_panel
            self.panel.update_str(
                self.request.user,
                initial_name,
                str_data,
                remove_gene=True if not str_data.get("gene") else False,
            )
            self.panel = GenePanel.objects.get(pk=self.panel.panel.pk).active_panel
            return self.panel.get_str(new_str_name)
        else:
            increment_version = (
                self.request.user.is_authenticated
                and self.request.user.reviewer.is_GEL()
            )
            str_item = self.panel.add_str(
                self.request.user, new_str_name, str_data, increment_version
            )
            return str_item
