from rest_framework import serializers
from panels.models import GenePanelSnapshot
from panels.models import GenePanelEntrySnapshot
from panels.models import STR
from panels.models import Region
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
            'mode_of_inheritance',
            'tags'
        )

    entity_type = serializers.CharField()
    entity_name = serializers.CharField()
    gene = serializers.JSONField()
    confidence_level = serializers.CharField(source='saved_gel_status')  # FIXME(Oleg) use old values or enum...
    mode_of_inheritance = serializers.CharField(source='moi')
    publications = NonEmptyItemsListField()
    phenotypes = NonEmptyItemsListField()
    evidence = EvidenceListField()
    tags = serializers.SlugRelatedField(
        many=True,
        read_only=True,
        slug_field='name'
    )


class GeneDetailSerializer(serializers.ModelSerializer):
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
            'mode_of_inheritance',
            'tags',
            'panel'
        )

    entity_type = serializers.CharField()
    entity_name = serializers.CharField()
    gene = serializers.JSONField()
    confidence_level = serializers.CharField(source='saved_gel_status')  # FIXME(Oleg) use old values or enum...
    mode_of_inheritance = serializers.CharField(source='moi')
    publications = NonEmptyItemsListField()
    phenotypes = NonEmptyItemsListField()
    evidence = EvidenceListField()
    panel = PanelListSerializer(many=False, read_only=True)
    tags = serializers.SlugRelatedField(
        many=True,
        read_only=True,
        slug_field='name'
    )


class STRSerializer(GeneSerializer):
    class Meta:
        model = STR
        fields = (
            'gene',
            'entity_type',
            'entity_name',
            'confidence_level',
            'penetrance',
            'publications',
            'evidence',
            'phenotypes',
            'mode_of_inheritance',
            'repeated_sequence',
            'chromosome',
            'grch37_coordinates',
            'grch38_coordinates',
            'normal_repeats',
            'pathogenic_repeats',
            'tags'
        )

    grch37_coordinates = RangeIntegerField(source='position_37')
    grch38_coordinates = RangeIntegerField(source='position_38')


class RegionSerializer(GeneSerializer):
    class Meta:
        model = Region
        fields = (
            'gene',
            'entity_type',
            'entity_name',
            'verbose_name',
            'confidence_level',
            'penetrance',
            'mode_of_pathogenicity',
            'haploinsufficiency_score',
            'triplosensitivity_score',
            'required_overlap_percentage',
            'type_of_variants',
            'publications',
            'evidence',
            'phenotypes',
            'mode_of_inheritance',
            'chromosome',
            'grch37_coordinates',
            'grch38_coordinates',
            'tags'
        )

    grch37_coordinates = RangeIntegerField(source='position_37')
    grch38_coordinates = RangeIntegerField(source='position_38')


class STRDetailSerializer(GeneDetailSerializer):
    class Meta:
        model = STR
        fields = (
            'gene',
            'entity_type',
            'entity_name',
            'confidence_level',
            'penetrance',
            'publications',
            'evidence',
            'phenotypes',
            'mode_of_inheritance',
            'repeated_sequence',
            'chromosome',
            'grch37_coordinates',
            'grch38_coordinates',
            'normal_repeats',
            'pathogenic_repeats',
            'panel',
            'tags'
        )

    grch37_coordinates = RangeIntegerField(source='position_37')
    grch38_coordinates = RangeIntegerField(source='position_38')
    panel = PanelListSerializer(many=False, read_only=True)


class RegionDetailSerializer(GeneDetailSerializer):
    class Meta:
        model = Region
        fields = (
            'gene',
            'entity_type',
            'entity_name',
            'verbose_name',
            'confidence_level',
            'penetrance',
            'mode_of_pathogenicity',
            'haploinsufficiency_score',
            'triplosensitivity_score',
            'required_overlap_percentage',
            'type_of_variants',
            'penetrance',
            'publications',
            'evidence',
            'phenotypes',
            'mode_of_inheritance',
            'chromosome',
            'grch37_coordinates',
            'grch38_coordinates',
            'panel',
            'tags'
        )

    grch37_coordinates = RangeIntegerField(source='position_37')
    grch38_coordinates = RangeIntegerField(source='position_38')
    panel = PanelListSerializer(many=False, read_only=True)


class PanelSerializer(PanelListSerializer):
    class Meta:
        model = GenePanelSnapshot
        fields = ('id', 'hash_id', 'name', 'disease_group', 'disease_sub_group', 'status',
                  'version', 'version_created', 'relevant_disorders', 'stats', 'genes', 'strs', 'regions')

    id = serializers.CharField(source='panel_id')
    hash_id = serializers.StringRelatedField(source='panel.old_pk')
    genes = GeneSerializer(source='get_all_genes_extra', many=True, read_only=True)
    strs = STRSerializer(source='get_all_strs_extra', many=True, read_only=True)
    regions = RegionSerializer(source='get_all_regions_extra', many=True, read_only=True)


class ActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Activity
        fields = ('created', 'panel_name', 'panel_id', 'panel_version',
                  'user_name', 'item_type', 'text', 'entity_name', 'entity_type')


class EvaluationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Evaluation
        fields = ('created', 'rating', 'mode_of_pathogenicity', 'publications', 'phenotypes', 'moi',
                  'current_diagnostic', 'clinically_relevant', )


class EntitiesListSerializer(serializers.ListSerializer):
    gene_serializer = None
    str_serializer = None
    region_serializer = None

    def __init__(self, *args, **kwargs):
        self.gene_serializer = GeneDetailSerializer()
        self.str_serializer = STRDetailSerializer()
        self.region_serializer = RegionDetailSerializer()
        super().__init__(*args, **kwargs)

    def to_representation(self, data):
        """
        List of object instances -> List of dicts of primitive datatypes.
        """

        types_to_serializers = {
            'gene': self.gene_serializer,
            'str': self.str_serializer,
            'region': self.region_serializer
        }

        return [
            types_to_serializers[item.entity_type].to_representation(item) for item in data
        ]


class EntitySerializer(serializers.BaseSerializer):
    class Meta:
        list_serializer_class = EntitiesListSerializer
