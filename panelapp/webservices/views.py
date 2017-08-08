from django.db import DatabaseError
from django.db.models import Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import permissions
from .utils import convert_moi
from .utils import convert_gel_status

from panels.models import GenePanel
from panels.models import GenePanelSnapshot
from panels.models import GenePanelEntrySnapshot
from .serializers import PanelSerializer
from .serializers import ListPanelSerializer
from .serializers import GenesSerializer


def filter_gene_list(gene_list, moi=None, mop=None, penetrance=None, conf_level=None, evidence=None):
    final_list = []
    for gene in gene_list:
        filters = True
        if gene.moi is not None and (moi is not None and convert_moi(gene.moi) not in moi):
            filters = False
        if gene.mode_of_pathogenicity is not None and (mop is not None and gene.mode_of_pathogenicity not in mop):
            filters = False
        if gene.penetrance is not None and (penetrance is not None and gene.penetrance not in penetrance):
            filters = False
        if conf_level is not None and convert_gel_status(gene.saved_gel_status) not in conf_level:
            filters = False
        if evidence is not None and not set([ev.name for ev in gene.evidence.all]).intersection(set(evidence)):
            filters = False
        if filters:
            final_list.append(gene)
    return final_list


@api_view(['GET'])
@permission_classes((permissions.AllowAny,))
def get_panel(request, panel_name):
    queryset = None
    gene_list = None
    filters = {}

    if "modesOfInheritance" in request.GET:
        filters["moi"] = request.GET["ModesOfInheritance"].split(",")
    if "ModeOfPathogenicity" in request.GET:
        filters["mode_of_pathogenicity"] = request.GET["ModesOfPathogenicity"].split(",")
    if "Penetrance" in request.GET:
        filters["penetrance"] = request.GET["Penetrance"].split(",")
    if "LevelOfConfidence" in request.GET:
        filters["conf_level"] = request.GET["LevelOfConfidence"].split(",")

    if "version" in request.GET:
        version = request.GET["version"]
        major_version = int(version.split(".")[0])
        minor_version = int(version.split(".")[1])
        queryset = GenePanel.objects.filter(name=panel_name)
        if not queryset:
            queryset = GenePanelSnapshot.objects.get_active().filter(old_panels__icontains=panel_name)
            if not queryset:
                try:
                    queryset = GenePanelSnapshot.objects.get_active().filter(panel__id=panel_name)
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
                queryset = GenePanelSnapshot.objects.filter(
                    panel__pk=panel_name,
                    major_version=major_version,
                    minor_version=minor_version
                )

            if not queryset:
                return Response({"Query Error: The version requested for panel:" + panel_name + " was not found."})

            gene_list = queryset[0].get_all_entries
            queryset = [queryset[0]]
        else:
            gene_list = queryset[0].get_all_entries

    else:
        queryset = GenePanelSnapshot.objects.get_active().filter(
            panel__name__icontains=panel_name,
            panel__approved=True
        )
        if not queryset:
            queryset = GenePanelSnapshot.objects.get_active().filter(
                old_panels__icontains=panel_name,
                panel__approved=True
            )
            if not queryset:
                try:
                    queryset = GenePanelSnapshot.objects.filter(panel__pk=panel_name, panel__approved=True)
                    if not queryset:
                        return Response({"Query Error: " + panel_name + " not found."})
                except (DatabaseError, ValueError):
                    return Response({"Query Error: " + panel_name + " not found."})

        gene_list = queryset[0].get_all_entries

    serializer = PanelSerializer(
        filter_gene_list(gene_list, **filters),
        instance=queryset[0],
        context={'request': request}
    )
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes((permissions.AllowAny,))
def list_panels(request):
    filters = {}
    if "Name" in request.GET:
        filters["panel__name__icontains"] = request.GET["Name"]

    queryset = GenePanelSnapshot.objects.get_active_anotated().filter(**filters)
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
        filters["moi__in"] = request.GET["ModeOfInheritance"].split(",")
    if "ModeOfPathogenicity" in request.GET:
        filters["mode_of_pathogenicity__in"] = request.GET["ModeOfPathogenicity"].split(",")
    if "Penetrance" in request.GET:
        filters["penetrance__in"] = request.GET["Penetrance"].split(",")
    if "LevelOfConfidence" in request.GET:
        post_filters["conf_level"] = request.GET["LevelOfConfidence"].split(",")
    if "Evidences" in request.GET:
        filters["evidence__name__in"] = request.GET["Evidences"].split(",")
    if "panel_name" in request.GET:
        panel_names = request.GET["panel_name"].split(",")
    else:
        panel_names = None

    if panel_names:
        all_panels = GenePanelSnapshot.objects.get_active().filter(panel__name__in=panel_names, panel__approved=True)
    else:
        all_panels = GenePanelSnapshot.objects.get_active().filter(panel__approved=True)

    panels_ids_dict = {panel.panel.pk: (panel.panel.pk, panel) for panel in all_panels}
    filters.update({'panel__panel__pk__in': list(panels_ids_dict.keys())})
    active_genes = GenePanelEntrySnapshot.objects.get_active()
    genes = active_genes.filter(**filters)

    if genes_qs:
        genes = genes.filter(genes_qs)

    serializer = GenesSerializer(
        filter_gene_list(genes, **post_filters),
        instance=queryset,
        context={'request': request}
    )
    data["results"] = serializer.to_representation(panels_ids_dict)
    data["meta"]["numOfResults"] = len(data["results"])
    return Response(data)
