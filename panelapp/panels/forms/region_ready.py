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
from panels.models import Region


class RegionReadyForm(forms.ModelForm):
    """
    This class marks Gene as Ready and also adds a comment if it was provided.
    It also saves a new evidence with the current Gene status as an evidence.
    Additionally, we add save a TrackRecord to note this change, and record an activity
    """

    ready_comment = forms.CharField(
        label="Comment (eg What decisions are being made?)",
        required=False,
        widget=forms.Textarea,
    )

    class Meta:
        model = Region
        fields = ("comments",)

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request")
        super().__init__(*args, **kwargs)

        original_fields = self.fields
        self.fields = {}
        self.fields["ready_comment"] = original_fields.get("ready_comment")

    def save(self, *args, **kwargs):
        self.instance.mark_as_ready(
            self.request.user, self.cleaned_data["ready_comment"]
        )
