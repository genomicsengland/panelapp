from django.db import DatabaseError
from django.db.models import Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import permissions
from .utils import convert_moi
from .utils import convert_mop
from .utils import convert_evidences
from .utils import convert_gel_status

from panels.models import GenePanel
from panels.models import GenePanelSnapshot
from panels.models import GenePanelEntrySnapshot
from .serializers import PanelSerializer
from .serializers import ListPanelSerializer
from .serializers import GenesSerializer


def filter_entity_list(entity_list, moi=None, mop=None, penetrance=None, conf_level=None, evidence=None):
    final_list = []
    for entity in entity_list:
        filters = True
        if entity.moi is not None and (moi is not None and convert_moi(entity.moi) not in moi):
            filters = False

        if entity.mode_of_pathogenicity is not None and (mop is not None and convert_mop(entity.mode_of_pathogenicity) not in mop):
            filters = False
        if entity.penetrance is not None and (penetrance is not None and entity.penetrance not in penetrance):
            filters = False
        if conf_level is not None and convert_gel_status(entity.saved_gel_status) not in conf_level:
            filters = False
        if evidence is not None and not set([ev.name for ev in entity.evidence.all]).intersection(set(evidence)):
            filters = False
        if filters:
            final_list.append(entity)
    return final_list


@api_view(['GET'])
@permission_classes((permissions.AllowAny,))
def get_panel(request, panel_name):
    queryset = None
    filters = {}

    if 'ModeOfInheritance' in request.GET:
        filters["moi"] = request.GET["ModeOfInheritance"].split(',')
    if "ModeOfPathogenicity" in request.GET:
        filters["mop"] = request.GET["ModeOfPathogenicity"].split(',')
    if "Penetrance" in request.GET:
        filters["penetrance"] = request.GET["Penetrance"].split(",")
    if "LevelOfConfidence" in request.GET:
        filters["conf_level"] = request.GET["LevelOfConfidence"].split(",")

    if "version" in request.GET:
        version = request.GET["version"]
        try:
            major_version = int(version.split(".")[0])
            minor_version = int(version.split(".")[1])
        except IndexError:
            return Response({"Query Error: The incorrect version requested"}, status=400)

        queryset = GenePanel.objects.filter(name=panel_name)
        if queryset.first():
            queryset = [queryset[0].active_panel]
        if not queryset:
            queryset = GenePanelSnapshot.objects.get_active(all=True, deleted=True, internal=True).filter(old_panels__icontains=panel_name)
            if not queryset:
                try:
                    try:
                        int(panel_name)
                        queryset = GenePanelSnapshot.objects.get_active(all=True, deleted=True, internal=True).filter(panel__id=panel_name)
                    except ValueError:
                        queryset = GenePanelSnapshot.objects.get_active(all=True, deleted=True, internal=True).filter(panel__old_pk=panel_name)
                    if not queryset:
                        return Response({"Query Error: " + panel_name + " not found."})
                except DatabaseError:
                    return Response({"Query Error: " + panel_name + " not found."})

        if major_version != queryset[0].major_version or minor_version != queryset[0].minor_version:
            queryset = GenePanelSnapshot.objects.filter(
                panel__name=panel_name,
                major_version=major_version,
                minor_version=minor_version
            )

            if not queryset:
                try:
                    int(panel_name)
                    queryset = GenePanelSnapshot.objects.filter(
                        panel__pk=panel_name,
                        major_version=major_version,
                        minor_version=minor_version
                    )
                except ValueError:
                    queryset = GenePanelSnapshot.objects.filter(
                        panel__old_pk=panel_name,
                        major_version=major_version,
                        minor_version=minor_version
                    )

            if not queryset:
                return Response({"Query Error: The version requested for panel:" + panel_name + " was not found."})

            queryset = [queryset[0]]
    else:
        queryset = GenePanelSnapshot.objects.get_active()

        queryset_name_exact = queryset.filter(panel__name=panel_name)
        if not queryset_name_exact:
            queryset_name = queryset.filter(panel__name__icontains=panel_name)
            if not queryset_name:
                queryset_old_names = queryset_name.filter(old_panels__icontains=panel_name)
                if not queryset_old_names:
                    try:
                        try:
                            int(panel_name)
                            queryset_pk = queryset.filter(panel__pk=panel_name)
                        except ValueError:
                            queryset_pk = queryset.filter(panel__old_pk=panel_name)

                        if not queryset_pk:
                            return Response({"Query Error: " + panel_name + " not found."})
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
        filter_entity_list(instance.get_all_genes, **filters),
        filter_entity_list(instance.get_all_strs, **filters),
        instance=instance,
        context={'request': request}
    )
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes((permissions.AllowAny,))
def list_panels(request):
    filters = {}
    if "Name" in request.GET:
        filters["panel__name__icontains"] = request.GET["Name"]

    if request.GET.get('Retired', '').lower() == 'true':
        queryset = GenePanelSnapshot.objects.get_active_annotated(all=True).filter(**filters)
    else:
        queryset = GenePanelSnapshot.objects.get_active_annotated().filter(**filters)

    serializer = ListPanelSerializer(instance=queryset,)
    return Response(serializer.data)


@api_view(['GET'])
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
        filters["moi__in"] = [convert_moi(x, True) for x in request.GET["ModeOfInheritance"].split(",") if convert_moi(x, True)]
    if "ModeOfPathogenicity" in request.GET:
        filters["mode_of_pathogenicity__in"] = [convert_mop(x, True) for x in request.GET["ModeOfPathogenicity"].split(",") if convert_mop(x, True)]
    if "Penetrance" in request.GET:
        filters["penetrance__in"] = request.GET["Penetrance"].split(",")
    if "LevelOfConfidence" in request.GET:
        post_filters["conf_level"] = request.GET["LevelOfConfidence"].split(",")
    if "Evidences" in request.GET:
        filters["evidence__name__in"] = [convert_evidences(x, True) for x in request.GET["Evidences"].split(",") if convert_evidences(x, True)]
    if "panel_name" in request.GET:
        panel_names = request.GET["panel_name"].split(",")
    else:
        panel_names = None

    if panel_names:
        all_panels = GenePanelSnapshot.objects.get_active().filter(panel__name__in=panel_names)
    else:
        all_panels = GenePanelSnapshot.objects.get_active()

    panels_ids_dict = {panel.panel.pk: (panel.panel.pk, panel) for panel in all_panels}
    filters.update({'panel__panel__pk__in': list(panels_ids_dict.keys())})
    active_genes = GenePanelEntrySnapshot.objects.get_active()
    genes = active_genes.filter(**filters)

    if genes_qs:
        genes = genes.filter(genes_qs)

    serializer = GenesSerializer(
        filter_entity_list(genes, **post_filters),
        instance=queryset,
        context={'request': request}
    )
    data["results"] = serializer.to_representation(panels_ids_dict)
    data["meta"]["numOfResults"] = len(data["results"])
    return Response(data)
