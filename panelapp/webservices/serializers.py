from rest_framework import serializers
from rest_framework.exceptions import APIException

from .utils import make_null
from .utils import convert_moi
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
    def __init__(self, list_of_genes, **kwargs):
        super(PanelSerializer, self).__init__(**kwargs)
        self.list_of_genes = list_of_genes

    def to_representation(self, panel):
        result = {
            "result": {
                "Genes": [],
                "SpecificDiseaseName": panel.panel.name,
                "version": panel.version,
                "DiseaseGroup": panel.level4title.level2title,
                "DiseaseSubGroup": panel.level4title.level3title
            }
        }

        for gene in self.list_of_genes:
            ensemblId = self.get_ensemblId(gene)
            result["result"]["Genes"].append({
                "GeneSymbol": gene.gene.get('gene_symbol'),
                "EnsembleGeneIds": ensemblId,
                "ModeOfInheritance": make_null(convert_moi(gene.moi)),
                "Penetrance": make_null(gene.penetrance),
                "Publications": make_null(gene.publications),
                "Phenotypes": make_null(gene.phenotypes),
                "ModeOfPathogenicity": make_null(gene.mode_of_pathogenicity),
                "LevelOfConfidence": convert_gel_status(gene.saved_gel_status),
                "Evidences": [ev.name for ev in gene.evidence.all()],
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
                "Number_of_Genes": panel.number_of_genes,
                "Panel_Id": panel.panel.old_pk if panel.panel.old_pk else str(panel.panel.pk),
                "Relevant_disorders": panel.old_panels
            })
        return result

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass

    def to_internal_value(self, data):
        pass
