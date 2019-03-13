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
from django.db.models import Q
from dal_select2.views import Select2QuerySetView
from dal_select2.views import Select2ListView
from panels.models import Gene
from panels.models import Evidence
from panels.models import Tag
from panels.models import GenePanelSnapshot
from panels.models import PanelType


class GeneAutocomplete(Select2QuerySetView):
    def get_queryset(self):
        qs = Gene.objects.filter(active=True)

        if self.q:
            qs = qs.filter(
                Q(gene_symbol__istartswith=self.q) | Q(gene_name__istartswith=self.q)
            )

        return qs


class SourceAutocomplete(Select2ListView):
    def get_list(self):
        return Evidence.ALL_SOURCES


class TagsAutocomplete(Select2QuerySetView):
    create_field = "name"

    def get_queryset(self):
        qs = Tag.objects.all()

        if self.q:
            qs = qs.filter(Q(name__istartswith=self.q) | Q(name__istartswith=self.q))

        return qs


class SimplePanelsAutocomplete(Select2QuerySetView):
    def get_queryset(self):
        qs = GenePanelSnapshot.objects.get_active_annotated(
            internal=False, deleted=False
        ).exclude(is_super_panel=True)

        if self.q:
            qs = qs.filter(
                Q(panel__name__icontains=self.q) | Q(panel__name__icontains=self.q)
            )

        return qs


class SimplePanelTypesAutocomplete(Select2QuerySetView):
    def get_queryset(self):
        qs = PanelType.objects.all()

        if self.q:
            qs = qs.filter(Q(name__icontains=self.q) | Q(name__icontains=self.q))

        return qs
