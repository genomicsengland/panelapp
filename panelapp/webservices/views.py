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
from django.conf import settings
from django.db import DatabaseError
from django.db.models import Q
from django.utils.functional import cached_property
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import permissions
from rest_framework import pagination
from rest_framework import generics
from .utils import convert_moi
from .utils import convert_mop
from .utils import convert_evidences
from .utils import convert_gel_status
from .utils import convert_confidence_level

from panels.models import GenePanel
from panels.models import GenePanelSnapshot
from panels.models import GenePanelEntrySnapshot
from panels.models import STR
from panels.models import Region
from panels.models import HistoricalSnapshot
from .serializers import PanelSerializer
from .serializers import GenesSerializer
from .serializers import EntitySerializer
from .serializers import ListPanelSerializer


def filter_entity_list(
    entity_list,
    moi=None,
    mop=None,
    penetrance=None,
    conf_level=None,
    evidence=None,
    haploinsufficiency_score=None,
    triplosensitivity_score=None,
):
    final_list = []
    for entity in entity_list:
        filters = True
        if entity.moi is not None and (
            moi is not None and convert_moi(entity.moi) not in moi
        ):
            filters = False

        if entity.mode_of_pathogenicity is not None and (
            mop is not None and convert_mop(entity.mode_of_pathogenicity) not in mop
        ):
            filters = False
        if entity.penetrance is not None and (
            penetrance is not None and entity.penetrance not in penetrance
        ):
            filters = False
        if (
            conf_level is not None
            and convert_gel_status(entity.saved_gel_status) not in conf_level
        ):
            filters = False
        if evidence is not None and not set(
            [ev.name for ev in entity.evidence.all]
        ).intersection(set(evidence)):
            filters = False

        if entity.is_region():
            if (
                haploinsufficiency_score
                and entity.haploinsufficiency_score not in haploinsufficiency_score
            ):
                filters = False
            if (
                triplosensitivity_score
                and entity.triplosensitivity_score not in triplosensitivity_score
            ):
                filters = False

        if filters:
            final_list.append(entity)
    return final_list


@api_view(["GET"])
@permission_classes((permissions.AllowAny,))
def get_panel(request, panel_name):
    queryset = None
    filters = {}

    if "ModeOfInheritance" in request.GET:
        filters["moi"] = request.GET["ModeOfInheritance"].split(",")
    if "ModeOfPathogenicity" in request.GET:
        filters["mop"] = request.GET["ModeOfPathogenicity"].split(",")
    if "Penetrance" in request.GET:
        filters["penetrance"] = request.GET["Penetrance"].split(",")
    if "LevelOfConfidence" in request.GET:
        filters["conf_level"] = request.GET["LevelOfConfidence"].split(",")
    if "HaploinsufficiencyScore" in request.GET:
        filters["haploinsufficiency_score"] = request.GET[
            "HaploinsufficiencyScore"
        ].split(",")
    if "TriplosensitivityScore" in request.GET:
        filters["triplosensitivity_score"] = request.GET[
            "TriplosensitivityScore"
        ].split(",")

    if "version" in request.GET:
        version = request.GET["version"]
        try:
            major_version = int(version.split(".")[0])
            minor_version = int(version.split(".")[1])
        except IndexError:
            return Response(
                {"Query Error: The incorrect version requested"}, status=400
            )

        snap = HistoricalSnapshot.objects.filter(
            panel__pk=panel_name,
            major_version=major_version,
            minor_version=minor_version,
        ).first()

        if not snap:
            return Response(
                {
                    "Query Error: The version requested for panel:"
                    + panel_name
                    + " was not found."
                }
            )
        json = snap.to_api_0()
        return Response(json)

    else:
        queryset = GenePanelSnapshot.objects.get_active()

        queryset_name_exact = queryset.filter(panel__name=panel_name)
        if not queryset_name_exact:
            queryset_name = queryset.filter(panel__name__icontains=panel_name)
            if not queryset_name:
                queryset_old_names = queryset_name.filter(
                    old_panels__icontains=panel_name
                )
                if not queryset_old_names:
                    try:
                        try:
                            int(panel_name)
                            queryset_pk = queryset.filter(panel__pk=panel_name)
                        except ValueError:
                            queryset_pk = queryset.filter(panel__old_pk=panel_name)

                        if not queryset_pk:
                            return Response(
                                {"Query Error: " + panel_name + " not found."}
                            )
                        else:
                            queryset = queryset_pk
                    except (DatabaseError, ValueError) as e:
                        return Response({"Query Error: " + panel_name + " not found."})
                else:
                    queryset = queryset_old_names
            else:
                queryset = queryset_name
        else:
            queryset = queryset_name_exact

    instance = queryset[0]
    serializer = PanelSerializer(
        filter_entity_list(instance.get_all_genes_extra, **filters),
        filter_entity_list(instance.get_all_strs_extra, **filters),
        filter_entity_list(instance.get_all_regions_extra, **filters),
        instance=instance,
        context={"request": request},
    )
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes((permissions.AllowAny,))
def list_panels(request):
    filters = {}
    if "Name" in request.GET:
        filters["panel__name__icontains"] = request.GET["Name"]

    if "Types" in request.GET:
        if request.GET["Types"] != "all":
            filters["panel__types__slug__in"] = request.GET["Types"].split(",")
    else:
        filters["panel__types__slug__in"] = settings.DEFAULT_PANEL_TYPES

    if request.GET.get("Retired", "").lower() == "true":
        queryset = GenePanelSnapshot.objects.get_active_annotated(all=True).filter(
            **filters
        )
    else:
        queryset = GenePanelSnapshot.objects.get_active_annotated().filter(**filters)

    serializer = ListPanelSerializer(instance=queryset)
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes((permissions.AllowAny,))
def search_by_gene(request, gene):
    queryset = None
    filters = {}
    post_filters = {}
    data = {"meta": {}, "results": []}

    genes_qs = None
    if gene != "all":
        for g in gene.split(","):
            if not genes_qs:
                genes_qs = Q(gene__gene_symbol=g)
            else:
                genes_qs = genes_qs | Q(gene__gene_symbol=g)

    if "ModeOfInheritance" in request.GET:
        filters["moi__in"] = [
            convert_moi(x, True)
            for x in request.GET["ModeOfInheritance"].split(",")
            if convert_moi(x, True)
        ]
    if "ModeOfPathogenicity" in request.GET:
        filters["mode_of_pathogenicity__in"] = [
            convert_mop(x, True)
            for x in request.GET["ModeOfPathogenicity"].split(",")
            if convert_mop(x, True)
        ]
    if "Penetrance" in request.GET:
        filters["penetrance__in"] = request.GET["Penetrance"].split(",")
    if "LevelOfConfidence" in request.GET:
        post_filters["conf_level"] = request.GET["LevelOfConfidence"].split(",")
    if "Evidences" in request.GET:
        filters["evidence__name__in"] = [
            convert_evidences(x, True)
            for x in request.GET["Evidences"].split(",")
            if convert_evidences(x, True)
        ]
    if "panel_name" in request.GET:
        panel_names = request.GET["panel_name"].split(",")
    else:
        panel_names = None

    if panel_names:
        all_panels = GenePanelSnapshot.objects.get_active_annotated().filter(
            panel__name__in=panel_names
        )
    else:
        all_panels = GenePanelSnapshot.objects.get_active_annotated()

    panels_ids_dict = {panel.panel.pk: (panel.panel.pk, panel) for panel in all_panels}
    filters.update({"panel__panel__pk__in": list(panels_ids_dict.keys())})
    active_genes = GenePanelEntrySnapshot.objects.get_active(
        pks=[s.pk for s in all_panels]
    )
    genes = active_genes.filter(**filters)

    if genes_qs:
        genes = genes.filter(genes_qs)

    serializer = GenesSerializer(
        filter_entity_list(genes, **post_filters),
        instance=queryset,
        context={"request": request},
    )
    data["results"] = serializer.to_representation(panels_ids_dict)
    data["meta"]["numOfResults"] = len(data["results"])
    return Response(data)


class EntitiesPagination(pagination.PageNumberPagination):
    page_size = 100
    page_size_query_param = "page_size"
    max_page_size = 200


class EntitiesListView(generics.ListAPIView):
    serializer_class = EntitySerializer
    pagination_class = EntitiesPagination

    @cached_property
    def snapshot_ids(self):
        if self.request.query_params.get("panel_name"):
            panel_names = self.request.query_params.get("panel_name").split(",")
        else:
            panel_names = None

        if panel_names:
            all_panels = GenePanelSnapshot.objects.get_active_annotated().filter(
                panel__name__in=panel_names
            )
        else:
            all_panels = GenePanelSnapshot.objects.get_active_annotated()

        return [s.pk for s in all_panels]

    def get_queryset(self):
        filters = {}

        if self.request.query_params.get("entity_name"):
            filters["entity_name__in"] = self.request.query_params.get(
                "entity_name"
            ).split(",")

        if self.request.query_params.get("ModeOfInheritance"):
            filters["moi__in"] = [
                convert_moi(x, True)
                for x in self.request.query_params.get("ModeOfInheritance").split(",")
                if convert_moi(x, True)
            ]

        if self.request.query_params.get("ModeOfPathogenicity"):
            filters["mode_of_pathogenicity__in"] = [
                convert_mop(x, True)
                for x in self.request.query_params.get("ModeOfPathogenicity").split(",")
                if convert_mop(x, True)
            ]

        if self.request.query_params.get("Penetrance"):
            filters["penetrance__in"] = self.request.query_params.get(
                "Penetrance"
            ).split(",")
        if self.request.query_params.get("LevelOfConfidence"):
            filters["saved_gel_status__in"] = [
                convert_confidence_level(level)
                for level in self.request.query_params.get("LevelOfConfidence").split(
                    ","
                )
                if level
            ]
        if self.request.query_params.get("Evidences"):
            filters["evidence__name__in"] = [
                convert_evidences(x, True)
                for x in self.request.query_params.get("Evidences").split(",")
                if convert_evidences(x, True)
            ]

        active_genes = GenePanelEntrySnapshot.objects.get_active_slim(
            pks=self.snapshot_ids
        )
        genes = active_genes.filter(**filters)

        active_strs = STR.objects.get_active_slim(pks=self.snapshot_ids)
        strs = active_strs.filter(**filters)

        active_regions = Region.objects.get_active_slim(pks=self.snapshot_ids)
        regions = active_regions.filter(**filters)

        return (
            strs.union(genes).union(regions).values("entity_name", "entity_type", "pk")
        )

    def list(self, request, *args, **kwargs):
        # We can't union two queries as they have different fields which fail on PostgreSQL level, due to field types
        # and count mismatch. Instead get the ids for a specific page, and then just get those values, create a joined
        # list, push to serializer.

        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        genes = GenePanelEntrySnapshot.objects.get_active(pks=self.snapshot_ids).filter(
            pk__in=[e.get("pk") for e in page if e.get("entity_type") == "gene"]
        )
        strs = STR.objects.get_active(pks=self.snapshot_ids).filter(
            pk__in=[e.get("pk") for e in page if e.get("entity_type") == "str"]
        )
        regions = Region.objects.get_active(pks=self.snapshot_ids).filter(
            pk__in=[e.get("pk") for e in page if e.get("entity_type") == "region"]
        )
        serializer = self.get_serializer(
            list(strs) + list(genes) + list(regions), many=True
        )
        return self.get_paginated_response(serializer.data)


list_entities = EntitiesListView.as_view()
