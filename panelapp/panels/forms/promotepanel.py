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
from django import forms
from panels.models import GenePanelSnapshot
from panels.tasks import increment_panel_async


class PromotePanelForm(forms.ModelForm):
    """
    This form increments a major version and saves new version comment
    """

    version_comment = forms.CharField(
        label="Comment about this new version", widget=forms.Textarea
    )

    class Meta:
        model = GenePanelSnapshot
        fields = ("version_comment",)

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request")
        super().__init__(*args, **kwargs)

    def save(self, *args, commit=True, **kwargs):
        increment_panel_async(
            self.instance.pk, self.request.user.pk, self.cleaned_data["version_comment"], major=True, include_superpanels=True
        )
