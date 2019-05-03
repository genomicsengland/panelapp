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
from math import ceil

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import permissions
from panels.models import GenePanelSnapshot
from panels.models import GenePanelEntrySnapshot
from panels.models import HistoricalSnapshot
from panels.models import STR
from panels.models import Region
from panels.models import Activity
from django import forms
from django.db.models import Q
from django.db.models import ObjectDoesNotExist
from django.utils.functional import cached_property
from django_filters import rest_framework as filters
from .serializers import PanelSerializer
from .serializers import ActivitySerializer
from .serializers import GeneSerializer
from .serializers import STRSerializer
from .serializers import EvaluationSerializer
from .serializers import RegionSerializer
from .serializers import EntitySerializer
from django.http import Http404
from rest_framework.exceptions import APIException


class ReadOnlyListViewset(
    viewsets.mixins.RetrieveModelMixin,
    viewsets.mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    pass


CONFIDENCE_CHOICES = ((3, "Green"), (2, "Amber"), (1, "Red"), (0, "No List"))


class NumberChoices(filters.ChoiceFilter, filters.NumberFilter):
    pass


class EntityFilter(filters.FilterSet):
    entity_name = filters.BaseInFilter(field_name="entity_name", lookup_expr="in")
    confidence_level = NumberChoices(
        method="filter_confidence_level",
        choices=CONFIDENCE_CHOICES,
        help_text="Filter by confidence level: 0, 1, 2, 3",
    )  # FIXME should be custom
    version = filters.CharFilter(method="version_lookup", help_text="Panel version")
    tags = filters.BaseInFilter(field_name="tags__name", lookup_expr="in")

    class Meta:
        fields = ["entity_name", "confidence_level", "tags"]

    def filter_confidence_level(self, queryset, name, value):
        field = "saved_gel_status"
        try:
            value = int(value)
            if value >= 3:
                value = 3
                field = field + "__gte"
        except ValueError:
            raise APIException(
                detail="Incorrect confidence level", code="incorrect_confidence_level"
            )

        return queryset.filter(**{field: value})

    def version_lookup(self, queryset, name, value):
        try:
            major, minor = value.split(".")
        except ValueError:
            raise APIException(
                detail="Incorrect version supplied", code="incorrect_version"
            )

        return queryset.filter(panel__major_version=major, panel__minor_version=minor)


class PanelsFilter(filters.FilterSet):
    type = filters.BaseInFilter(field_name="panel__types__slug", lookup_expr="in")

    class Meta:
        fields = ["type"]


class PanelsViewSet(ReadOnlyListViewset):
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)
    lookup_value_regex = "[^/]+"
    serializer_class = PanelSerializer
    filter_class = PanelsFilter

    def get_serializer(self, *args, **kwargs):
        if self.action == "retrieve":
            kwargs["include_entities"] = True
        return super().get_serializer(*args, **kwargs)

    def get_queryset(self):
        retired = self.request.query_params.get("retired", False)
        name = self.request.query_params.get("name", None)
        return GenePanelSnapshot.objects.get_active_annotated(all=retired, name=name)

    def get_object(self):
        obj = GenePanelSnapshot.objects.get_active_annotated(
            name=self.kwargs["pk"]
        ).first()

        if obj:
            return obj

        raise Http404

    def retrieve(self, request, *args, **kwargs):
        """Get individual Panel data

        In addition to the model fields this endpoint also returns `genes`, `strs`, `regions` associated with this panel.

        Additional parameters:

        ?version=1.1 - get a specific version for this panel
        """
        version = self.request.query_params.get("version", None)
        if version:
            try:
                major_version, minor_version = version.split(".")
            except ValueError:
                raise APIException(
                    detail="Incorrect version supplied", code="incorrect_version"
                )
            snap = HistoricalSnapshot.objects.filter(panel__pk=self.kwargs["pk"],
                                                     major_version=major_version,
                                                     minor_version=minor_version).first()
            if snap:
                json = snap.to_api_1()
                return Response(json)
            else:
                raise Http404
        return super().retrieve(request, *args, **kwargs)

    @action(detail=True)
    def versions(self, request, pk=None):
        versions = GenePanelSnapshot.objects.get_panel_snapshots(pk)

        page = self.paginate_queryset(versions)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(versions, many=True)
        return Response(serializer.data)

    @action(detail=True)
    def activities(self, request, pk=None):
        if request.user.is_authenticated and request.user.reviewer.is_GEL():
            activities = Activity.objects.visible_to_gel()
        else:
            activities = Activity.objects.visible_to_public()

        activities = activities.filter(Q(panel_id=pk) | Q(extra_data__panel_id=pk))

        return Response(ActivitySerializer(activities, many=True).data)


class ActivityViewSet(viewsets.mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)
    serializer_class = ActivitySerializer

    def get_queryset(self):
        if self.request.user.is_authenticated and self.request.user.reviewer.is_GEL():
            return Activity.objects.visible_to_gel()
        else:
            return Activity.objects.visible_to_public()


class EntityViewSet(viewsets.mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)
    lookup_field = "entity_name"
    lookup_url_kwarg = "entity_name"

    def filter_list(self, object):
        entity_name = self.request.query_params.get("entity_name")
        confidence_level = self.request.query_params.get("confidence_level")
        tags = self.request.query_params.get("tags")

        if entity_name and confidence_level and tags:
            if object['entity_name'] in entity_name.split(',') and object['confidence_level'] == confidence_level and [True for tag in tags.split(',') if tag in object['tags']]:
                return True
            else:
                return False
        elif entity_name and confidence_level:
            if object['entity_name'] in entity_name.split(',') and object['confidence_level'] == confidence_level:
                return True
            else:
                return False
        elif entity_name and tags:
            if object['entity_name'] in entity_name.split(',') and [True for tag in tags.split(',') if tag in object['tags']]:
                return True
            else:
                return False
        elif confidence_level and tags:
            if object['confidence_level'] == confidence_level and [True for tag in tags.split(',') if tag in object['tags']]:
                return True
            else:
                return False
        elif entity_name:
            if object['entity_name'] in entity_name.split(','):
                return True
            else:
                return False
        elif confidence_level:
            if object['confidence_level'] == confidence_level:
                return True
            else:
                return False
        elif tags:
            for tag in tags.split(','):
                if tag in object['tags']:
                    return True
            else:
                return False
        else:
            return True

    def list(self, request, *args, **kwargs):
        version = self.request.query_params.get("version", None)
        if version:
            try:
                major_version, minor_version = version.split(".")
            except ValueError:
                raise APIException(
                    detail="Incorrect version supplied", code="incorrect_version"
                )

            obj = HistoricalSnapshot.objects.filter(panel__pk=self.kwargs["panel_pk"],
                                                    major_version=major_version,
                                                    minor_version=minor_version).first()

            if obj:
                count = len(obj.data['genes'])
                start = 0
                finish = 100
                page = self.request.query_params.get("page", None)
                response = {"count": count, "next": None, "previous": None, "results": []}
                max_pages = ceil(count / 100)

                if max_pages > 1:
                    if page:
                        page = int(page)
                        start = (page - 1) * 100
                        finish = page * 100
                        next_page = (page + 1) if page + 1 <= max_pages else None
                        previous_page = (page - 1) if page - 1 >= 1 else None
                        if next_page:
                            response["next"] = request.build_absolute_uri().replace('&page='+str(page), '&page=' + str(next_page))
                        if previous_page:
                            response["previous"] = request.build_absolute_uri().replace('&page='+str(page), '&page=' + str(previous_page))

                    else:
                        response["next"] = request.build_absolute_uri() + '&page=2'

                collection = obj.data[self.lookup_collection]

                collection = list(filter(self.filter_list, collection))

                for gene in collection[start:finish]:
                    response['results'].append(gene)

                response["count"] = len(collection)
                return Response(response)
            else:
                raise Http404
        else:
            return super().list(request, *args, **kwargs)

    def get_panel(self):
        version = self.request.query_params.get("version")
        if version:
            obj = GenePanelSnapshot.objects.get_panel_version(
                name=self.kwargs["panel_pk"], version=version
            ).first()
        else:
            obj = GenePanelSnapshot.objects.get_active_annotated(
                all=True, internal=True, deleted=True, name=self.kwargs["panel_pk"]
            ).first()

        if obj:
            return obj

        raise Http404


class GeneViewSet(EntityViewSet):
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)
    serializer_class = GeneSerializer
    filter_class = EntityFilter
    lookup_collection = 'genes'

    def get_queryset(self):
        version = self.request.query_params.get("version", None)
        if version:
            return GenePanelEntrySnapshot.objects.none()
        else:
            obj = GenePanelSnapshot.objects.get_active_annotated(
                all=True, internal=True, deleted=True, name=self.kwargs["panel_pk"]
            ).first()
            return obj.get_all_genes.prefetch_related("evidence", "tags")

class GeneEvaluationsViewSet(EntityViewSet):
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)
    serializer_class = EvaluationSerializer

    def get_queryset(self):
        panel = self.get_panel()
        try:
            gene = panel.get_gene(self.kwargs["gene_entity_name"])
            return gene.evaluation.all()
        except ObjectDoesNotExist:
            raise Http404


class STRViewSet(EntityViewSet):
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)
    serializer_class = STRSerializer
    filter_class = EntityFilter
    lookup_collection = 'strs'


    def get_queryset(self):
        return self.get_panel().get_all_strs.prefetch_related("evidence", "tags")


class STREvaluationsViewSet(EntityViewSet):
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)
    serializer_class = EvaluationSerializer

    def get_queryset(self):
        panel = self.get_panel()
        try:
            str_item = panel.get_str(self.kwargs["str_entity_name"])
            return str_item.evaluation.all()
        except ObjectDoesNotExist:
            raise Http404


class RegionViewSet(EntityViewSet):
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)
    filter_backends = (filters.DjangoFilterBackend,)
    serializer_class = RegionSerializer
    filter_class = EntityFilter
    lookup_collection = 'regions'


    def get_queryset(self):
        return self.get_panel().get_all_regions.prefetch_related("evidence", "tags")


class RegionEvaluationsViewSet(EntityViewSet):
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)
    serializer_class = EvaluationSerializer

    def get_queryset(self):
        panel = self.get_panel()
        try:
            region = panel.get_region(self.kwargs["region_entity_name"])
            return region.evaluation.all()
        except ObjectDoesNotExist:
            raise Http404


class EntitySearchFilter(filters.FilterSet):
    type = filters.BaseInFilter(
        field_name="panel__panel__types__slug", lookup_expr="in"
    )
    tags = filters.BaseInFilter(field_name="tags__name", lookup_expr="in")
    entity_name = filters.BaseInFilter(field_name="entity_name", lookup_expr="in")

    class Meta:
        fields = ["type", "tags", "entity_name"]


class EntitySearch(ReadOnlyListViewset):
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)
    lookup_field = "entity_name"
    lookup_url_kwarg = "entity_name"
    filter_class = EntitySearchFilter

    @property
    def active_snapshot_ids(self):
        panel_names = self.request.query_params.get("panel_name", "")
        if panel_names:
            all_panels = (
                GenePanelSnapshot.objects.get_active_annotated()
                .filter(panel__name__in=panel_names.split(","))
                .values_list("pk", flat=True)
            )
        else:
            all_panels = GenePanelSnapshot.objects.get_active_annotated().values_list(
                "pk", flat=True
            )

        return list(all_panels)

    @property
    def qs_filters(self):
        filters = {}

        if self.kwargs.get("entity_name"):
            filters["entity_name__in"] = self.kwargs["entity_name"].split(",")
        elif self.request.query_params.get("entity_name"):
            filters["entity_name__in"] = self.request.query_params["entity_name"].split(
                ","
            )

        if self.request.query_params.get("type"):
            filters["panel__panel__types__slug__in"] = self.request.query_params[
                "type"
            ].split(",")

        if self.request.query_params.get("tags"):
            filters["tags__name__in"] = self.request.query_params["tags"].split(",")

        return filters


class GeneSearchViewSet(EntitySearch):
    """Search Genes"""

    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)
    serializer_class = GeneSerializer

    def get_queryset(self):
        filters = {"pks": self.active_snapshot_ids}

        return GenePanelEntrySnapshot.objects.get_active(**filters).filter(
            **self.qs_filters
        )

    def retrieve(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


class STRSearchViewSet(EntitySearch):
    """Search STRs"""

    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)
    serializer_class = STRSerializer

    def get_queryset(self):
        filters = {"pks": self.active_snapshot_ids}

        return STR.objects.get_active(**filters).filter(**self.qs_filters)

    def retrieve(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


class RegionSearchViewSet(EntitySearch):
    """Search Regions"""

    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)
    serializer_class = RegionSerializer

    def get_queryset(self):
        filters = {"pks": self.active_snapshot_ids}

        return Region.objects.get_active(**filters).filter(**self.qs_filters)

    def retrieve(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


class EntitySearchViewSet(EntitySearch):
    """Search Entities"""

    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)
    serializer_class = EntitySerializer
    filter_class = EntitySearchFilter

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

        return all_panels.values_list("pk", flat=True)

    def get_queryset(self):
        filters = {}

        if self.kwargs.get("entity_name"):
            filters["entity_name__in"] = self.kwargs["entity_name"].split(",")
        elif self.request.query_params.get("entity_name"):
            filters["entity_name__in"] = self.request.query_params["entity_name"].split(
                ","
            )

        if self.request.query_params.get("type"):
            filters["panel__panel__types__slug__in"] = self.request.query_params[
                "type"
            ].split(",")

        if self.request.query_params.get("tags"):
            filters["tag__name__in"] = self.request.query_params["tags"].split(",")

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
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)

        genes = GenePanelEntrySnapshot.objects.get_active().filter(
            pk__in=[e.get("pk") for e in page if e.get("entity_type") == "gene"]
        )
        strs = STR.objects.get_active().filter(
            pk__in=[e.get("pk") for e in page if e.get("entity_type") == "str"]
        )
        regions = Region.objects.get_active().filter(
            pk__in=[e.get("pk") for e in page if e.get("entity_type") == "region"]
        )

        serializer = self.get_serializer(
            list(genes) + list(strs) + list(regions), many=True
        )

        return self.get_paginated_response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)
