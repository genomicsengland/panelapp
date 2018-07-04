from rest_framework import serializers
from panels.models import GenePanelSnapshot
from panels.models import GenePanelEntrySnapshot
from panels.models import STR
from panels.models import Activity
from panels.models import Evaluation


class NonEmptyItemsListField(serializers.ListField):
    def to_representation(self, data):
        return [self.child.to_representation(item).strip() for item in data if item]


class StatsJSONField(serializers.JSONField):
    def to_representation(self, value):
        whitelist_stats = [
            'number_of_genes',
            'number_of_strs',
            'number_of_regions'
        ]
        out = {}
        for val in whitelist_stats:
            if val in value:
                out[val] = value[val]
        return out


class RangeIntegerField(serializers.CharField):
    def to_representation(self, value):
        return [value.lower, value.upper] if value else None


class EvidenceListField(serializers.ListField):
    def to_representation(self, data):
        return data.values_list('name', flat=True) if data else []


class GeneSerializer(serializers.ModelSerializer):
    class Meta:
        model = GenePanelEntrySnapshot
        fields = (
            'gene',
            'entity_type',
            'entity_name',
            'confidence_level',
            'penetrance',
            'mode_of_pathogenicity',
            'publications',
            'evidence',
            'phenotypes',
            'mode_of_inheritance'
        )

    entity_type = serializers.CharField()
    entity_name = serializers.CharField()
    gene = serializers.JSONField()
    confidence_level = serializers.CharField(source='saved_gel_status')  # FIXME(Oleg) use old values or enum...
    mode_of_inheritance = serializers.CharField(source='moi')
    publications = NonEmptyItemsListField()
    phenotypes = NonEmptyItemsListField()
    evidence = EvidenceListField()


class STRSerializer(GeneSerializer):
    class Meta:
        model = STR
        fields = (
            'gene',
            'entity_type',
            'entity_name',
            'confidence_level',
            'penetrance',
            'mode_of_pathogenicity',
            'publications',
            'evidence',
            'phenotypes',
            'mode_of_inheritance',
            'repeated_sequence',
            'chromosome',
            'position_37',
            'position_38',
            'normal_repeats',
            'pathogenic_repeats'
        )

    position_37 = RangeIntegerField()
    position_38 = RangeIntegerField()


class PanelVersionListSerializer(serializers.ModelSerializer):
    class Meta:
        model = GenePanelSnapshot
        fields = ('version', 'version_created', )

    version = serializers.CharField(read_only=True)
    version_created = serializers.DateTimeField(source='created', read_only=True)


class PanelListSerializer(serializers.ModelSerializer):
    class Meta:
        model = GenePanelSnapshot
        fields = ('id', 'hash_id', 'name', 'disease_group', 'disease_sub_group', 'status',
                  'version', 'version_created', 'relevant_disorders', 'stats')

    id = serializers.IntegerField(source='panel_id')
    hash_id = serializers.StringRelatedField(source='panel.old_pk')
    name = serializers.StringRelatedField(source='level4title.name')
    disease_group = serializers.StringRelatedField(source='level4title.level2title')
    disease_sub_group = serializers.StringRelatedField(source='level4title.level3title')
    status = serializers.StringRelatedField(source='panel.status')
    version = serializers.CharField(read_only=True)
    version_created = serializers.DateTimeField(source='created', read_only=True)
    relevant_disorders = NonEmptyItemsListField(source='old_panels')
    stats = StatsJSONField(help_text="Object with panel statistics (number of genes or STRs)", read_only=True)


class PanelSerializer(PanelListSerializer):
    class Meta:
        model = GenePanelSnapshot
        fields = ('id', 'hash_id', 'name', 'disease_group', 'disease_sub_group', 'status',
                  'version', 'version_created', 'relevant_disorders', 'stats', 'genes', 'strs')

    id = serializers.CharField(source='panel_id')
    hash_id = serializers.StringRelatedField(source='panel.old_pk')
    genes = GeneSerializer(source='get_all_genes_extra', many=True, read_only=True)
    strs = STRSerializer(source='get_all_strs_extra', many=True, read_only=True)


class ActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Activity
        fields = ('created', 'panel_name', 'panel_id', 'panel_version',
                  'user_name', 'item_type', 'text', 'entity_name', 'entity_type')


class EvaluationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Evaluation
        fields = ('created', 'rating', 'mode_of_pathogenicity', 'publications', 'phenotypes', 'moi',
                  'current_diagnostic', 'clinically_relevant',)