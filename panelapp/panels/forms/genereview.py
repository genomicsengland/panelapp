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
from collections import OrderedDict
from django import forms
from .helpers import GELSimpleArrayField
from panels.models import Evaluation


class GeneReviewForm(forms.ModelForm):
    class Meta:
        model = Evaluation
        exclude = ("user", "version", "comments", "clinically_relevant")

    publications = GELSimpleArrayField(
        forms.CharField(),
        label="Publications (PMID: 1234;4321)",
        delimiter=";",
        required=False,
    )
    phenotypes = GELSimpleArrayField(
        forms.CharField(),
        label="Phenotypes (separate using a semi-colon - ;)",
        delimiter=";",
        required=False,
    )

    rating = forms.ChoiceField(
        choices=[("", "Provide rating")] + Evaluation.RATINGS, required=False
    )
    current_diagnostic = forms.BooleanField(required=False)
    comments = forms.CharField(widget=forms.Textarea, required=False)

    def __init__(self, *args, **kwargs):
        self.panel = kwargs.pop("panel")
        self.request = kwargs.pop("request")
        self.gene = kwargs.pop("gene")
        super().__init__(*args, **kwargs)

        original_fields = self.fields

        self.fields = OrderedDict()
        self.fields["rating"] = original_fields.get("rating")
        self.fields["moi"] = original_fields.get("moi")
        self.fields["mode_of_pathogenicity"] = original_fields.get(
            "mode_of_pathogenicity"
        )
        self.fields["publications"] = original_fields.get("publications")
        self.fields["phenotypes"] = original_fields.get("phenotypes")
        self.fields["current_diagnostic"] = original_fields.get("current_diagnostic")
        self.fields["comments"] = original_fields.get("comments")

    def clean_phenotypes(self):
        clean_data = [p.replace('\t', ' ') for p in self.cleaned_data.get('phenotypes')]
        return clean_data

    def save(self, *args, **kwargs):
        evaluation_data = self.cleaned_data
        evaluation_data["comment"] = evaluation_data.pop("comments")
        panel = self.gene.panel
        ev = panel.get_gene(self.gene.gene.get("gene_symbol")).update_evaluation(
            self.request.user, evaluation_data
        )
        panel._update_saved_stats()
        return ev
