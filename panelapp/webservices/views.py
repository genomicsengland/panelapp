from django.db import DatabaseError
from django.db.models import Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import permissions
from .utils import convert_moi
from .utils import convert_mop
from .utils import convert_evidences

from panels.models import GenePanel
from panels.models import GenePanelSnapshot
from panels.models import GenePanelEntrySnapshot
from backups.models import PanelBackup
from .serializers import PanelSerializer
from .serializers import ListPanelSerializer
from .serializers import GenesSerializer
from webservices.serializers import PanelBackupSerializer


@api_view(['GET'])
@permission_classes((permissions.AllowAny,))
def get_panel(request, panel_name):
    queryset = None
    gene_list = None
    filters = {}

    if 'ModeOfInheritance' in request.GET:
        filters["moi"] = request.GET["ModeOfInheritance"].split(',')
    if "ModeOfPathogenicity" in request.GET:
        filters["mop"] = request.GET["ModeOfPathogenicity"].split(',')
    if "Penetrance" in request.GET:
        filters["penetrance"] = request.GET["Penetrance"].split(",")
    if "LevelOfConfidence" in request.GET:
        filters["conf_level"] = request.GET["LevelOfConfidence"].split(",")

    version_filter = None
    if "version" in request.GET:
        queryset = GenePanel.objects.filter(name=panel_name)
        if queryset.first():
            queryset = [queryset[0].active_panel]
        if not queryset:
            queryset = GenePanelSnapshot.objects.get_active(all=True, deleted=True).filter(old_panels__icontains=panel_name)
        try:
            major_version, minor_version = request.GET["version"].split('.')
            version_filter = Q(major_version=major_version) & Q(minor_version=minor_version)
        except ValueError:
            return Response({"Query Error: Incorrect version {}".format(request.GET['version'])}, status_code=400)

    try:
        name_filter = Q(original_pk=int(panel_name))
    except ValueError:
        name_filter = Q(name=panel_name) | Q(old_pk=panel_name)

    if version_filter:
        name_filter = name_filter & version_filter

    backup_panel = PanelBackup.objects.filter(name_filter).first()
    if not backup_panel:
        old_panels_filter = Q(old_panels__icontains=panel_name)
        if version_filter:
            old_panels_filter = old_panels_filter & version_filter
        backup_panel = PanelBackup.objects.filter(old_panels_filter).first()

    if backup_panel:
        serializer = PanelBackupSerializer(
            backup_panel.genes_content['result']['Genes'],
            filters,
            instance=backup_panel,
            context={'request': request}
        )
    else:
        # return Response({"Query Error: " + panel_name + " not found."}, status_code=404)  # waiting until we have all the backups populated
        # The code below should be removed after we populate backup records.
        # Right now we check if we have records in the backup panels, if not,
        # we still revert back to the quering the models.
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
                queryset = GenePanelSnapshot.objects.get_active(all=True, deleted=True).filter(old_panels__icontains=panel_name)
                if not queryset:
                    try:
                        try:
                            int(panel_name)
                            queryset = GenePanelSnapshot.objects.get_active(all=True, deleted=True).filter(panel__id=panel_name)
                        except ValueError:
                            queryset = GenePanelSnapshot.objects.get_active(all=True, deleted=True).filter(panel__old_pk=panel_name)
                        if not queryset:
                            return Response({"Query Error: " + panel_name + " not found."}, status_code=404)
                    except DatabaseError:
                        return Response({"Query Error: " + panel_name + " not found."}, status_code=404)

            if major_version != queryset[0].major_version or minor_version != queryset[0].minor_version:
                queryset = GenePanelSnapshot.objects.filter(
                    panel__name=panel_name,
                    major_version=major_version,
                    minor_version=minor_version
                )

                if not queryset:
                    try:
                        int(panel_name)
                        queryset = GenePanelSnapshot.objects.get_active(all=True, deleted=True).filter(panel__id=panel_name)
                    except ValueError:
                        queryset = GenePanelSnapshot.objects.get_active(all=True, deleted=True).filter(panel__old_pk=panel_name)
                        if not queryset:
                            return Response({"Query Error: " + panel_name + " not found."})
                    except DatabaseError:
                        return Response({"Query Error: " + panel_name + " not found."})

                if not queryset:
                    return Response({"Query Error: The version requested for panel:" + panel_name + " was not found."}, status_code=404)

                gene_list = queryset[0].get_all_entries
                queryset = [queryset[0]]
            else:
                gene_list = queryset[0].get_all_entries
        else:
            queryset = GenePanelSnapshot.objects.get_active(all=True, deleted=True)

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
                            return Response({"Query Error: " + panel_name + " not found."}, status_code=404)
                        else:
                            queryset = queryset_pk
                    except (DatabaseError, ValueError) as e:
                        return Response({"Query Error: " + panel_name + " not found."}, status_code=404)
                else:
                    queryset = queryset_old_names
            else:
                queryset = queryset_name
            gene_list = queryset[0].get_all_entries

        serializer = PanelSerializer(
            gene_list,
            filters,
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

    if "Retired" in request.GET and request.GET['Retired'] == 'True':
        queryset = GenePanelSnapshot.objects.get_active_anotated(all=True, deleted=True).filter(**filters)
    else:
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
        all_panels = GenePanelSnapshot.objects.get_active(deleted=True).filter(panel__name__in=panel_names, panel__approved=True)
    else:
        all_panels = GenePanelSnapshot.objects.get_active(deleted=True).filter(panel__approved=True)

    panels_ids_dict = {panel.panel.pk: (panel.panel.pk, panel) for panel in all_panels}
    filters.update({'panel__panel__pk__in': list(panels_ids_dict.keys())})
    active_genes = GenePanelEntrySnapshot.objects.get_active(deleted=True)
    genes = active_genes.filter(**filters)

    if genes_qs:
        genes = genes.filter(genes_qs)

    serializer = GenesSerializer(
        genes,
        post_filters,
        instance=queryset,
        context={'request': request}
    )
    data["results"] = serializer.to_representation(panels_ids_dict)
    data["meta"]["numOfResults"] = len(data["results"])
    return Response(data)
