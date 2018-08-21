import logging
from rest_framework import serializers
from rest_framework.exceptions import APIException

from .utils import make_null
from .utils import convert_moi
from .utils import filter_empty
from .utils import convert_gel_status


class EnsembleIdMixin:
    def get_ensemblId(self, gene):
        query_prams = self.context['request'].query_params
        assembly = 'GRch37'
        version = '82'
        if 'assembly' in query_prams:
            if query_prams['assembly'].lower() == 'grch38':
                assembly = 'GRch38'
                version = '90'
            elif query_prams['assembly'].lower() == 'grch37':
                assembly = 'GRch37'
                version = '82'
            else:
                raise NotAcceptedValue(detail='Unaccepted value for assembly, please use: GRch37 or GRch38')

        ensemblId = None
        if gene.gene:
            if assembly == 'GRch38' and gene.gene.get('ensembl_genes'):
                ensemblId = gene.gene.get('ensembl_genes', {}).get(assembly, {}).get(version, {}).get('ensembl_id', None)
            elif assembly == 'GRch37':
                if gene.gene.get('ensembl_genes'):
                    ensemblId = gene.gene.get('ensembl_genes', {}).get(assembly, {}).get(version, {}).get('ensembl_id', None)
                elif gene.gene.get('other_transcripts') and len(gene.gene.get('other_transcripts')) > 0:
                    ensemblId = gene.gene.get('other_transcripts', [{}])[0].get('geneid', None)

        if ensemblId is None:
            return []
        return [ensemblId]


class NotAcceptedValue(APIException):
    status_code = 404
    default_detail = 'Unaccepted value for one of the fields.'
    default_code = 'bad_request'


class PanelSerializer(EnsembleIdMixin, serializers.BaseSerializer):
    def __init__(self, list_of_genes, list_of_strs, list_of_regions, **kwargs):
        super(PanelSerializer, self).__init__(**kwargs)
        self.list_of_genes = list_of_genes
        self.list_of_strs = list_of_strs
        self.list_of_regions = list_of_regions

    def to_representation(self, panel):
        result = {
            "result": {
                "Genes": [],
                "STRs": [],
                "Regions": [],
                "SpecificDiseaseName": panel.panel.name,
                "version": panel.version,
                "Created": panel.created,
                "DiseaseGroup": panel.level4title.level2title,
                "DiseaseSubGroup": panel.level4title.level3title,
                "Status": panel.panel.status
            }
        }

        for gene in self.list_of_genes:
            result["result"]["Genes"].append({
                "GeneSymbol": gene.gene.get('gene_symbol'),
                "EnsembleGeneIds": self.get_ensemblId(gene),
                "ModeOfInheritance": make_null(convert_moi(gene.moi)),
                "Penetrance": make_null(gene.penetrance),
                "Publications": make_null(gene.publications),
                "Phenotypes": make_null(gene.phenotypes),
                "ModeOfPathogenicity": make_null(gene.mode_of_pathogenicity),
                "LevelOfConfidence": convert_gel_status(gene.saved_gel_status),
                "Evidences": [ev.name for ev in gene.evidence.all()],
            })

        for str_item in self.list_of_strs:
            result["result"]["STRs"].append({
                "Name": str_item.name,
                "Chromosome": str_item.chromosome,
                "GRCh37Coordinates": [str_item.position_37.lower, str_item.position_37.upper],
                "GRCh38Coordinates": [str_item.position_38.lower, str_item.position_38.upper],
                "RepeatedSequence": str_item.repeated_sequence,
                "NormalRepeats": str_item.normal_repeats,
                "PathogenicRepeats": str_item.pathogenic_repeats,
                "GeneSymbol": str_item.gene.get('gene_symbol') if str_item.gene else None,
                "EnsembleGeneIds": self.get_ensemblId(str_item),
                "ModeOfInheritance": make_null(convert_moi(str_item.moi)),
                "Penetrance": make_null(str_item.penetrance),
                "Publications": make_null(str_item.publications),
                "Phenotypes": make_null(str_item.phenotypes),
                "LevelOfConfidence": convert_gel_status(str_item.saved_gel_status),
                "Evidences": [ev.name for ev in str_item.evidence.all()],
            })

        for region in self.list_of_regions:
            result["result"]["Regions"].append({
                "Name": region.name,
                "VerboseName": region.verbose_name,
                "Chromosome": region.chromosome,
                "GRCh37Coordinates": [region.position_37.lower, region.position_37.upper],
                "GRCh38Coordinates": [region.position_38.lower, region.position_38.upper],
                "HaploinsufficiencyScore": region.haploinsufficiency_score,
                "TriplosensitivityScore": region.triplosensitivity_score,
                "RequiredOverlapPercentage": region.required_overlap_percentage,
                "GeneSymbol": region.gene.get('gene_symbol') if region.gene else None,
                "EnsembleGeneIds": self.get_ensemblId(region),
                "ModeOfInheritance": make_null(convert_moi(region.moi)),
                "Penetrance": make_null(region.penetrance),
                "TypeOfVariants": region.type_of_variants,
                "Publications": make_null(region.publications),
                "Phenotypes": make_null(region.phenotypes),
                "LevelOfConfidence": convert_gel_status(region.saved_gel_status),
                "Evidences": [ev.name for ev in region.evidence.all()],
            })

        return result

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass

    def to_internal_value(self, data):
        pass


class GenesSerializer(EnsembleIdMixin, serializers.BaseSerializer):
    def __init__(self, list_of_genes, **kwargs):
        super().__init__(**kwargs)
        self.list_of_genes = list_of_genes

    def update(self, instance, validated_data):
        pass

    def to_representation(self, panels):
        result = []
        super_panels = {}  # used to remove duplicated super panels
        for gene in self.list_of_genes:
            panel = panels[gene.panel.panel.pk][1]
            ensemblId = self.get_ensemblId(gene)
            result.append({
                "GeneSymbol": gene.gene.get('gene_symbol'),
                "EnsembleGeneIds": ensemblId,
                "ModeOfInheritance": make_null(convert_moi(gene.moi)),
                "Penetrance": make_null(gene.penetrance),
                "Publications": make_null(gene.publications),
                "Phenotypes": make_null(gene.phenotypes),
                "ModeOfPathogenicity": make_null(gene.mode_of_pathogenicity),
                "LevelOfConfidence": convert_gel_status(gene.saved_gel_status),
                "version":  panel.version,
                "SpecificDiseaseName": panel.level4title.name,
                "DiseaseGroup": panel.level4title.level2title,
                "DiseaseSubGroup": panel.level4title.level3title,
                "Evidences": [ev.name for ev in gene.evidence.all()],
            })

            if panel.is_child_panel:
                # the same child panel can be linked in multiple super panel versions, this is normal, we need
                # to normalize data and only display the latest version
                for parent_panel in panel.genepanelsnapshot_set.all()\
                        .distinct('panel_id').order_by('panel_id', '-major_version', '-minor_version')\
                        .prefetch_related('level4title'):
                    if super_panels.get(parent_panel.panel_id) is None:
                        super_panels[parent_panel.panel_id] = []

                    super_panels[parent_panel.panel_id].append({
                        "GeneSymbol": gene.gene.get('gene_symbol'),
                        "EnsembleGeneIds": ensemblId,
                        "ModeOfInheritance": make_null(convert_moi(gene.moi)),
                        "Penetrance": make_null(gene.penetrance),
                        "Publications": make_null(gene.publications),
                        "Phenotypes": make_null(gene.phenotypes),
                        "ModeOfPathogenicity": make_null(gene.mode_of_pathogenicity),
                        "LevelOfConfidence": convert_gel_status(gene.saved_gel_status),
                        "version": parent_panel.version,
                        "SpecificDiseaseName": parent_panel.level4title.name,
                        "DiseaseGroup": parent_panel.level4title.level2title,
                        "DiseaseSubGroup": parent_panel.level4title.level3title,
                        "Evidences": [ev.name for ev in gene.evidence.all()],
                    })

        for genes in super_panels.values():
            for gene in genes:
                result.append(gene)

        return result

    def create(self, validated_data):
        pass

    def to_internal_value(self, data):
        pass


class ListPanelSerializer(serializers.BaseSerializer):
    def to_representation(self, array_of_panels):
        result = {"result": []}

        for panel in array_of_panels:
            result["result"].append({
                "Name": panel.panel.name,
                "DiseaseSubGroup": panel.level4title.level3title,
                "DiseaseGroup": panel.level4title.level2title,
                "CurrentVersion": panel.version,
                "CurrentCreated": panel.created,
                "Number_of_Genes": panel.stats.get('number_of_genes'),
                "Number_of_STRs": panel.stats.get('number_of_strs'),
                "Number_of_Regions": panel.stats.get('number_of_regions'),
                "Panel_Id": panel.panel.old_pk if panel.panel.old_pk else str(panel.panel.pk),
                "Relevant_disorders": filter(filter_empty, panel.old_panels),
                "Status": panel.panel.status
            })
        return result

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass

    def to_internal_value(self, data):
        pass


class EntitySerializer(EnsembleIdMixin, serializers.BaseSerializer):
    def to_representation(self, entity):
        out = {
            "GeneSymbol": entity.gene.get('gene_symbol') if entity.gene else None,
            "EntityType": entity.entity_type,
            "EnsembleGeneIds": self.get_ensemblId(entity) if entity.gene else None,
            "ModeOfInheritance": make_null(convert_moi(entity.moi)),
            "Penetrance": make_null(entity.penetrance),
            "Publications": make_null(entity.publications),
            "Phenotypes": make_null(entity.phenotypes),
            "LevelOfConfidence": convert_gel_status(entity.saved_gel_status),
            "Evidences": [ev.name for ev in entity.evidence.all()],
            "Panel": {
                "Name": entity.panel.panel.name,
                "DiseaseSubGroup": entity.panel.level4title.level3title,
                "DiseaseGroup": entity.panel.level4title.level2title,
                "CurrentVersion": entity.panel.version,
                "CurrentCreated": entity.panel.created,
                "Panel_Id": entity.panel.panel.old_pk if entity.panel.panel.old_pk else str(entity.panel.panel.pk),
                "Relevant_disorders": filter(filter_empty, entity.panel.old_panels),
                "Status": entity.panel.panel.status,
            }
        }

        if entity.entity_type == 'gene':
            out["ModeOfPathogenicity"] = make_null(entity.mode_of_pathogenicity)
        elif entity.entity_type == 'str':
            out["Name"] = entity.name
            out["Chromosome"] = entity.chromosome
            out["GRCh37Coordinates"] = [entity.position_37.lower, entity.position_37.upper]
            out["GRCh38Coordinates"] = [entity.position_38.lower, entity.position_38.upper]
            out["RepeatedSequence"] = entity.repeated_sequence
            out["NormalRepeats"] = entity.normal_repeats
            out["PathogenicRepeats"] = entity.pathogenic_repeats
        elif entity.entity_type == 'region':
            out["Name"] = entity.name
            out["VerboseName"] = entity.verbose_name
            out["Chromosome"] = entity.chromosome
            out["GRCh37Coordinates"] = [entity.position_37.lower, entity.position_37.upper]
            out["GRCh38Coordinates"] = [entity.position_38.lower, entity.position_38.upper]
            out["HaploinsufficiencyScore"] = entity.haploinsufficiency_score
            out["TriplosensitivityScore"] = entity.triplosensitivity_score
            out["RequiredOverlapPercentage"] = entity.required_overlap_percentage
        else:
            raise Exception('Incorrect entity type for {}'.format(entity))

        return out

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass

    def to_internal_value(self, data):
        pass
