import copy
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
        if assembly == 'GRch38' and gene.get('ensembl_genes'):
            ensemblId = gene.get('ensembl_genes', {}).get(assembly, {}).get(version, {}).get('ensembl_id', None)
        elif assembly == 'GRch37':
            if gene.get('ensembl_genes'):
                ensemblId = gene.get('ensembl_genes', {}).get(assembly, {}).get(version, {}).get('ensembl_id', None)
            elif gene.get('other_transcripts') and len(gene.get('other_transcripts')) > 0:
                ensemblId = gene.get('other_transcripts', [{}])[0].get('geneid', None)

        if ensemblId is None:
            return []
        return [ensemblId]


class NotAcceptedValue(APIException):
    status_code = 404
    default_detail = 'Unaccepted value for one of the fields.'
    default_code = 'bad_request'


class GenesPostFilterMixin:
    def filter_gene_list(self, gene_list, moi=None, mop=None, penetrance=None, conf_level=None, evidence=None):
        final_list = []
        for gene in gene_list:
            filters = True
            if gene.moi is not None and (moi is not None and convert_moi(gene.moi) not in moi):
                filters = False

            if gene.mode_of_pathogenicity is not None and (mop is not None and convert_mop(gene.mode_of_pathogenicity) not in mop):
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


class PanelSerializer(EnsembleIdMixin, GenesPostFilterMixin, serializers.BaseSerializer):
    def __init__(self, list_of_genes, post_filters, **kwargs):
        super().__init__(**kwargs)
        self.list_of_genes = self.filter_gene_list(list_of_genes, **post_filters)

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
            ensemblId = self.get_ensemblId(gene.gene)
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


class GenesSerializer(EnsembleIdMixin, GenesPostFilterMixin, serializers.BaseSerializer):
    def __init__(self, list_of_genes, post_filters, **kwargs):
        super().__init__(**kwargs)
        self.list_of_genes = self.filter_gene_list(list_of_genes, **post_filters)

    def update(self, instance, validated_data):
        pass

    def to_representation(self, panels):
        result = []
        for gene in self.list_of_genes:
            panel = panels[gene.panel.panel.pk][1]
            ensemblId = self.get_ensemblId(gene.gene)
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
                "Relevant_disorders": filter(filter_empty, panel.old_panels)
            })
        return result

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass

    def to_internal_value(self, data):
        pass


class PanelBackupSerializer(EnsembleIdMixin, serializers.BaseSerializer):
    def __init__(self, list_of_genes, post_filters, **kwargs):
        super().__init__(**kwargs)
        self.list_of_genes = self.filter_gene_list(list_of_genes, **post_filters)

    def filter_gene_list(self, gene_list, moi=None, mop=None, penetrance=None, conf_level=None, evidence=None):
        final_list = []
        for gene in gene_list:
            filters = True
            ModeOfInheritance = gene.get('ModeOfInheritance')
            if ModeOfInheritance and moi and ModeOfInheritance not in moi:
                filters = False

            ModeOfPathogenicity = gene.get('ModeOfPathogenicity')
            if ModeOfPathogenicity and mop and ModeOfPathogenicity not in mop:
                filters = False

            Penetrance = gene.get('Penetrance')
            if Penetrance and penetrance and Penetrance not in penetrance:
                filters = False

            LevelOfConfidence = gene.get('LevelOfConfidence')
            if LevelOfConfidence and conf_level and LevelOfConfidence not in conf_level:
                filters = False

            Evidences = gene.get('Evidences')
            if Evidences and evidence and not set(Evidences).intersection(set(evidence)):
                filters = False

            if filters:
                final_list.append(gene)
        return final_list

    def to_representation(self, panel):
        result = panel.genes_content
        del result['result']['__gel__internal']
        result['result']['Genes'] = []

        for gene in self.list_of_genes:
            ensemblId = self.get_ensemblId(gene['__gel_internal']['gene_data'])
            del gene['__gel_internal']
            gene['EnsembleGeneIds'] = ensemblId
            result['result']['Genes'].append(gene)
        return result

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass

    def to_internal_value(self, data):
        pass
