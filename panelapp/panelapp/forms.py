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


class Select2ListMultipleChoiceField(forms.MultipleChoiceField):
    def __init__(
        self,
        choice_list=None,
        required=True,
        widget=None,
        label=None,
        initial=None,
        help_text="",
        *args,
        **kwargs
    ):
        choice_list = choice_list or []
        if callable(choice_list):
            choices = [(choice, choice) for choice in choice_list()]
        else:
            choices = [(choice, choice) for choice in choice_list]

        super(Select2ListMultipleChoiceField, self).__init__(
            choices=choices,
            required=required,
            widget=widget,
            label=label,
            initial=initial,
            help_text=help_text,
            *args,
            **kwargs
        )
