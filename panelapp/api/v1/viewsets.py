from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import permissions
from panels.models import GenePanelSnapshot
from panels.models import GenePanelEntrySnapshot
from panels.models import STR
from panels.models import Region
from panels.models import Activity
from django.db.models import Q
from django.db.models import ObjectDoesNotExist
from django.utils.functional import cached_property
from .serializers import PanelSerializer
from .serializers import ActivitySerializer
from .serializers import GeneSerializer
from .serializers import STRSerializer
from .serializers import EvaluationSerializer
from .serializers import RegionSerializer
from .serializers import EntitySerializer
from django.http import Http404
from rest_framework.exceptions import APIException


class ReadOnlyListViewset(viewsets.mixins.RetrieveModelMixin, viewsets.mixins.ListModelMixin, viewsets.GenericViewSet):
    pass


class PanelTypesFilterMixin:
    def panel_types_filters(self):
        return [pt for pt in self.request.query_params.get('type', '').split(',') if pt]


class PanelsViewSet(PanelTypesFilterMixin, ReadOnlyListViewset):
    permission_classes = (permissions.IsAuthenticatedOrReadOnly, )
    lookup_value_regex = '[^/]+'
    serializer_class = PanelSerializer

    def get_serializer(self, *args, **kwargs):
        if self.action == 'retrieve':
            kwargs['include_entities'] = True
        return super().get_serializer(*args, **kwargs)

    def get_queryset(self):
        retired = self.request.query_params.get('retired', False)
        name = self.request.query_params.get('name', None)
        return GenePanelSnapshot.objects.get_active_annotated(all=retired, name=name, panel_types=self.panel_types_filters())

    def get_object(self):
        version = self.request.query_params.get('version', None)
        if version:
            try:
                _, _ = version.split('.')
            except ValueError:
                raise APIException(detail='Incorrect version supplied', code='incorrect_version')

            obj = GenePanelSnapshot.objects.get_panel_version(name=self.kwargs['pk'], version=version).first()
        else:
            obj = GenePanelSnapshot.objects.get_active_annotated(name=self.kwargs['pk']).first()

        if obj:
            return obj

        raise Http404

    def retrieve(self, request, *args, **kwargs):
        """Get individual Panel data

        In addition to the model fields this endpoint also returns `genes`, `strs`, `regions` associated with this panel."""

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
    lookup_field = 'entity_name'
    lookup_url_kwarg = 'entity_name'

    def get_panel(self):
        obj = GenePanelSnapshot.objects.get_active_annotated(
            all=True, internal=True, deleted=True, name=self.kwargs['panel_pk']).first()

        if obj:
            return obj

        raise Http404

    def filter_by_tag(self, qs):
        tags = self.request.query_params.get('tags', '')
        if tags:
            qs = qs.filter(tags__name__in=tags.split(','))
        return qs


class GeneViewSet(EntityViewSet):
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)
    serializer_class = GeneSerializer

    def get_queryset(self):
        panel = self.get_panel()
        return self.filter_by_tag(panel.get_all_genes)


class GeneEvaluationsViewSet(EntityViewSet):
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)
    serializer_class = EvaluationSerializer

    def get_queryset(self):
        panel = self.get_panel()
        try:
            gene = panel.get_gene(self.kwargs['gene_entity_name'])
            return gene.evaluation.all()
        except ObjectDoesNotExist:
            raise Http404


class STRViewSet(EntityViewSet):
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)
    serializer_class = STRSerializer

    def get_queryset(self):
        panel = self.get_panel()
        return self.filter_by_tag(panel.get_all_strs)


class STREvaluationsViewSet(EntityViewSet):
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)
    serializer_class = EvaluationSerializer

    def get_queryset(self):
        panel = self.get_panel()
        try:
            str_item = panel.get_str(self.kwargs['str_entity_name'])
            return str_item.evaluation.all()
        except ObjectDoesNotExist:
            raise Http404


class RegionViewSet(EntityViewSet):
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)
    serializer_class = RegionSerializer

    def get_queryset(self):
        panel = self.get_panel()
        return self.filter_by_tag(panel.get_all_regions)


class RegionEvaluationsViewSet(EntityViewSet):
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)
    serializer_class = EvaluationSerializer

    def get_queryset(self):
        panel = self.get_panel()
        try:
            region = panel.get_region(self.kwargs['region_entity_name'])
            return region.evaluation.all()
        except ObjectDoesNotExist:
            raise Http404


class EntitySearchViewSet(PanelTypesFilterMixin, ReadOnlyListViewset):
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)
    lookup_field = 'entity_name'
    lookup_url_kwarg = 'entity_name'

    @property
    def active_snapshot_ids(self):
        panel_names = self.request.query_params.get('panel_name', '')
        if panel_names:
            all_panels = GenePanelSnapshot.objects.get_active_annotated() \
                .filter(panel__name__in=panel_names.split(',')) \
                .values_list('pk', flat=True)
        else:
            all_panels = GenePanelSnapshot.objects.get_active_annotated() \
                .values_list('pk', flat=True)

        return list(all_panels)

    def filter_by_tag(self, qs):
        tags = self.request.query_params.get('tags', '')
        if tags:
            qs = qs.filter(tags__name__in=tags.split(','))
        return qs


class GeneSearchViewSet(EntitySearchViewSet):
    """Search Genes"""
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)
    serializer_class = GeneSerializer

    def get_queryset(self):
        filters = {
            'pks': self.active_snapshot_ids
        }
        if self.kwargs.get('entity_name'):
            filters['gene_symbol'] = self.kwargs['entity_name'].split(',')
            filters['panel_types'] = self.panel_types_filters()

        return self.filter_by_tag(GenePanelEntrySnapshot.objects.get_active(**filters))

    def retrieve(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


class STRSearchViewSet(EntitySearchViewSet):
    """Search STRs"""
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)
    serializer_class = STRSerializer

    def get_queryset(self):
        filters = {
            'pks': self.active_snapshot_ids
        }
        if self.kwargs.get('entity_name'):
            filters['name'] = self.kwargs['entity_name'].split(',')
            filters['panel_types'] = self.panel_types_filters()

        return self.filter_by_tag(STR.objects.get_active(**filters))

    def retrieve(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


class RegionSearchViewSet(EntitySearchViewSet):
    """Search Regions"""
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)
    serializer_class = RegionSerializer

    def get_queryset(self):
        filters = {
            'pks': self.active_snapshot_ids
        }
        if self.kwargs.get('entity_name'):
            filters['name'] = self.kwargs['entity_name'].split(',')
            filters['panel_types'] = self.panel_types_filters()

        return self.filter_by_tag(Region.objects.get_active(**filters))

    def retrieve(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


class EntitySearchViewSet(EntitySearchViewSet):
    """Search Entities"""
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)
    serializer_class = EntitySerializer

    @cached_property
    def snapshot_ids(self):
        if self.request.query_params.get('panel_name'):
            panel_names = self.request.query_params.get("panel_name").split(",")
        else:
            panel_names = None

        get_active_filters = {
            'panel_types': self.panel_types_filters()
        }

        if panel_names:
            all_panels = GenePanelSnapshot.objects.get_active_annotated(**get_active_filters)\
                .filter(panel__name__in=panel_names)
        else:
            all_panels = GenePanelSnapshot.objects.get_active_annotated(**get_active_filters)

        return [s.get('pk') for s in all_panels.values('pk')]

    def get_queryset(self):
        filters = {}

        if self.kwargs.get('entity_name'):
            filters['entity_name__in'] = self.kwargs['entity_name'].split(',')

        active_genes = GenePanelEntrySnapshot.objects.get_active(pks=self.snapshot_ids)
        genes = active_genes.filter(**filters)

        active_strs = STR.objects.get_active(pks=self.snapshot_ids)
        strs = active_strs.filter(**filters)

        active_regions = Region.objects.get_active(pks=self.snapshot_ids)
        regions = active_regions.filter(**filters)

        return strs.union(genes).union(regions).values('entity_name', 'entity_type', 'pk')

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)

        genes = GenePanelEntrySnapshot.objects.get_active(pks=self.snapshot_ids) \
            .filter(pk__in=[e.get('pk') for e in page if e.get('entity_type') == 'gene'])
        strs = STR.objects.get_active(pks=self.snapshot_ids) \
            .filter(pk__in=[e.get('pk') for e in page if e.get('entity_type') == 'str'])
        regions = Region.objects.get_active(pks=self.snapshot_ids) \
            .filter(pk__in=[e.get('pk') for e in page if e.get('entity_type') == 'region'])

        serializer = self.get_serializer(list(genes) + list(strs) + list(regions), many=True)

        return self.get_paginated_response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)
