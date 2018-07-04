from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import permissions
from panels.models import GenePanelSnapshot
from panels.models import Activity
from django.db.models import Q
from .serializers import PanelListSerializer
from .serializers import PanelSerializer
from .serializers import PanelVersionListSerializer
from .serializers import ActivitySerializer
from .serializers import GeneSerializer
from .serializers import STRSerializer
from .serializers import EvaluationSerializer
from django.http import Http404


class ReadOnlyListViewset(viewsets.mixins.RetrieveModelMixin, viewsets.mixins.ListModelMixin, viewsets.GenericViewSet):
    pass


class PanelsViewSet(ReadOnlyListViewset):
    permission_classes = (permissions.IsAuthenticated, )

    def get_serializer_class(self):
        if self.action == 'list':
            return PanelListSerializer
        elif self.action == 'retrieve':
            return PanelSerializer
        elif self.action == 'versions':
            return PanelVersionListSerializer

    def get_queryset(self):
        retired = self.request.query_params.get('retired', False)
        name = self.request.query_params.get('name', None)
        return GenePanelSnapshot.objects.get_active_annotated(all=retired, name=name)

    def get_object(self):
        obj = GenePanelSnapshot.objects.get_active_annotated(
            all=True, internal=True, deleted=True, name=self.kwargs['pk']).first()

        if obj:
            return obj

        raise Http404

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
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = ActivitySerializer

    def get_queryset(self):
        if self.request.user.is_authenticated and self.request.user.reviewer.is_GEL():
            return Activity.objects.visible_to_gel()
        else:
            return Activity.objects.visible_to_public()


class EntityViewSet(viewsets.mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = (permissions.IsAuthenticated,)
    lookup_field = 'entity_name'
    lookup_url_kwarg = 'entity_name'

    def get_panel(self):
        obj = GenePanelSnapshot.objects.get_active_annotated(
            all=True, internal=True, deleted=True, name=self.kwargs['panel_pk']).first()

        if obj:
            return obj

        raise Http404

    @action(detail=True)
    def evaluations(self, request, panel_pk=None, entity_name=None):
        panel = self.get_panel()
        if self.serializer_class == GeneSerializer:
            entity = panel.get_gene(entity_name)
        elif self.serializer_class == STRSerializer:
            entity = panel.get_str(entity_name)

        return Response(EvaluationSerializer(entity.evaluation.all(), many=True).data)


class GeneViewSet(EntityViewSet):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = GeneSerializer

    def get_queryset(self):
        panel = self.get_panel()
        return panel.get_all_genes


class STRViewSet(EntityViewSet):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = STRSerializer

    def get_queryset(self):
        panel = self.get_panel()
        return panel.get_all_strs
