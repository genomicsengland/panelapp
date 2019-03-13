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


class ActivityFilterForm(forms.Form):
    panel = forms.ChoiceField(required=False, choices=list)
    version = forms.ChoiceField(required=False, choices=list)
    entity = forms.ChoiceField(label="Gene or Genomic Entity Name", required=False, choices=list)
    date_from = forms.DateField(required=False,
                                widget=forms.DateInput(attrs={
                                    'type': 'date',
                                    'placeholder': 'Date in YYYY-MM-DD format',
                                    'pattern': '[0-9]{4}-[0-9]{2}-[0-9]{2}'
                                }))
    date_to = forms.DateField(required=False,
                              widget=forms.DateInput(attrs={
                                  'type': 'date',
                                  'placeholder': 'Date in YYYY-MM-DD format',
                                  'pattern': '[0-9]{4}-[0-9]{2}-[0-9]{2}'
                              }))

    def __init__(self, *args, **kwargs):
        panels = kwargs.pop('panels')
        versions = kwargs.pop('versions')
        entities = kwargs.pop('entities')

        super().__init__(*args, **kwargs)

        self.fields['panel'].choices = [('', 'Panel')] + list(panels)

        if versions:
            self.fields['version'].choices = [('', 'Panel Version')] + list(versions)
        else:
            self.fields['version'].widget.attrs = {'disabled': 'disabled'}

        if entities:
            self.fields['entity'].choices = [('', '')] + list(entities)
        else:
            self.fields['entity'].widget.attrs = {'disabled': 'disabled'}
