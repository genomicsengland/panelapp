##
## Copyright (c) 2016-2019 Genomics England Ltd.
##
## This file is part of PanelApp
## (see https://panelapp.genomicsengland.co.uk).
##
## Licensed to the Apache Software Foundation (ASF) under one
## or more contributor license agreements.  See the NOTICE file
## distributed with this work for additional information
## regarding copyright ownership.  The ASF licenses this file
## to you under the Apache License, Version 2.0 (the
## "License"); you may not use this file except in compliance
## with the License.  You may obtain a copy of the License at
##
##   http://www.apache.org/licenses/LICENSE-2.0
##
## Unless required by applicable law or agreed to in writing,
## software distributed under the License is distributed on an
## "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
## KIND, either express or implied.  See the License for the
## specific language governing permissions and limitations
## under the License.
##
from rest_framework import serializers
from panels.models import GenePanelSnapshot
from panels.models import GenePanelEntrySnapshot
from panels.models import STR
from panels.models import Region
from panels.models import Activity
from panels.models import Evaluation
from panels.models import PanelType


class NonEmptyItemsListField(serializers.ListField):
    def to_representation(self, data):
        return [self.child.to_representation(item).strip() for item in data if item]


class StatsJSONField(serializers.JSONField):
    def to_representation(self, value):
        whitelist_stats = ["number_of_genes", "number_of_strs", "number_of_regions"]
        out = {}
        for val in whitelist_stats:
            if val in value:
                out[val] = value[val]
        return out


class RangeIntegerField(serializers.ListField):
    def to_representation(self, value):
        return [value.lower, value.upper] if value else None

    def to_internal_value(self, data):
        raise NotImplementedError("Implement it when we add adding genes")


class EvidenceListField(serializers.ListField):
    def to_representation(self, data):
        if data:
            return [e.name for e in data.all()]
        return []


class PanelTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PanelType
        fields = ("name", "slug", "description")


class PanelSerializer(serializers.ModelSerializer):
    class Meta:
        model = GenePanelSnapshot
        fields = (
            "id",
            "hash_id",
            "name",
            "disease_group",
            "disease_sub_group",
            "status",
            "version",
            "version_created",
            "relevant_disorders",
            "stats",
            "types",
        )
        depth = 1

    id = serializers.IntegerField(source="panel_id")
    hash_id = serializers.StringRelatedField(source="panel.old_pk")
    name = serializers.StringRelatedField(source="level4title.name")
    disease_group = serializers.StringRelatedField(source="level4title.level2title")
    disease_sub_group = serializers.StringRelatedField(source="level4title.level3title")
    status = serializers.StringRelatedField(source="panel.status")
    version = serializers.CharField(read_only=True)
    version_created = serializers.DateTimeField(source="created", read_only=True)
    relevant_disorders = NonEmptyItemsListField(source="old_panels")
    stats = StatsJSONField(
        help_text="Object with panel statistics (number of genes or STRs)",
        read_only=True,
    )
    types = PanelTypeSerializer(source="panel.types", read_only=True, many=True)

    def __init__(self, *args, **kwargs):
        self.include_entities = False
        if kwargs.get("include_entities", False):
            kwargs.pop("include_entities")
            self.include_entities = True

        super().__init__(*args, **kwargs)

        no_panel = True

        if self.instance and isinstance(self.instance, GenePanelSnapshot):
            if self.instance.is_super_panel:
                no_panel = False

        if self.include_entities:
            self.fields["genes"] = GeneSerializer(
                source="get_all_genes_prefetch",
                many=True,
                read_only=True,
                no_panel=no_panel,
            )
            self.fields["strs"] = STRSerializer(
                source="get_all_strs_prefetch",
                many=True,
                read_only=True,
                no_panel=no_panel,
            )
            self.fields["regions"] = RegionSerializer(
                source="get_all_regions_prefetch",
                many=True,
                read_only=True,
                no_panel=no_panel,
            )


class GeneData(serializers.JSONField):
    alias_name = serializers.CharField(allow_null=True, allow_blank=True)
    ensembl_genes = serializers.DictField()
    hgnc_date_symbol_changed = serializers.DateField()
    hgnc_symbol = serializers.CharField()
    alias = serializers.ListField(
        child=serializers.CharField(allow_blank=False, allow_null=False)
    )
    hgnc_release = serializers.DateTimeField()
    biotype = serializers.CharField()
    gene_symbol = serializers.CharField()
    hgnc_id = serializers.CharField()
    gene_name = serializers.CharField()
    omim_gene = serializers.ListField(
        child=serializers.CharField(allow_null=False, allow_blank=False)
    )


class GeneSerializer(serializers.ModelSerializer):
    class Meta:
        model = GenePanelEntrySnapshot
        fields = (
            "gene_data",
            "entity_type",
            "entity_name",
            "confidence_level",
            "penetrance",
            "mode_of_pathogenicity",
            "publications",
            "evidence",
            "phenotypes",
            "mode_of_inheritance",
            "tags",
            "panel",
        )

    entity_type = serializers.CharField()
    entity_name = serializers.CharField()
    gene_data = GeneData(source="gene", read_only=True)
    confidence_level = serializers.CharField(
        source="saved_gel_status"
    )  # FIXME(Oleg) use old values or enum...
    mode_of_inheritance = serializers.CharField(source="moi")
    publications = NonEmptyItemsListField()
    phenotypes = NonEmptyItemsListField()
    evidence = EvidenceListField()
    tags = serializers.SlugRelatedField(many=True, read_only=True, slug_field="name")
    panel = PanelSerializer(many=False, read_only=True, required=False, allow_null=True)

    def __init__(self, *args, **kwargs):
        self.no_panel = False
        if kwargs.get("no_panel", False):
            self.no_panel = True
        if "no_panel" in kwargs:
            kwargs.pop("no_panel")
        super().__init__(*args, **kwargs)
        if self.no_panel:
            del self.fields["panel"]

    def get_field_names(self, declared_fields, info):
        field_names = super().get_field_names(declared_fields, info)
        if self.no_panel:
            return [n for n in field_names if field_names != "panel"]
        return field_names


class STRSerializer(GeneSerializer):
    class Meta:
        model = STR
        fields = (
            "gene_data",
            "entity_type",
            "entity_name",
            "confidence_level",
            "penetrance",
            "publications",
            "evidence",
            "phenotypes",
            "mode_of_inheritance",
            "repeated_sequence",
            "chromosome",
            "grch37_coordinates",
            "grch38_coordinates",
            "normal_repeats",
            "pathogenic_repeats",
            "tags",
            "panel",
        )

    grch37_coordinates = RangeIntegerField(
        child=serializers.IntegerField(allow_null=False),
        source="position_37",
        min_length=2,
        max_length=2,
    )
    grch38_coordinates = RangeIntegerField(
        child=serializers.IntegerField(allow_null=False),
        source="position_38",
        min_length=2,
        max_length=2,
    )


class RegionSerializer(GeneSerializer):
    class Meta:
        model = Region
        fields = (
            "gene_data",
            "entity_type",
            "entity_name",
            "verbose_name",
            "confidence_level",
            "penetrance",
            "mode_of_pathogenicity",
            "haploinsufficiency_score",
            "triplosensitivity_score",
            "required_overlap_percentage",
            "type_of_variants",
            "publications",
            "evidence",
            "phenotypes",
            "mode_of_inheritance",
            "chromosome",
            "grch37_coordinates",
            "grch38_coordinates",
            "tags",
            "panel",
        )

    grch37_coordinates = RangeIntegerField(
        child=serializers.IntegerField(allow_null=False),
        source="position_37",
        min_length=2,
        max_length=2,
    )
    grch38_coordinates = RangeIntegerField(
        child=serializers.IntegerField(allow_null=False),
        source="position_38",
        min_length=2,
        max_length=2,
    )


class ActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Activity
        fields = (
            "created",
            "panel_name",
            "panel_id",
            "panel_version",
            "user_name",
            "item_type",
            "text",
            "entity_name",
            "entity_type",
        )


class EvaluationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Evaluation
        fields = (
            "created",
            "rating",
            "mode_of_pathogenicity",
            "publications",
            "phenotypes",
            "moi",
            "current_diagnostic",
            "clinically_relevant",
        )


class EntitiesListSerializer(serializers.ListSerializer):
    gene_serializer = None
    str_serializer = None
    region_serializer = None

    def __init__(self, *args, **kwargs):
        self.gene_serializer = GeneSerializer()
        self.str_serializer = STRSerializer()
        self.region_serializer = RegionSerializer()
        super().__init__(*args, **kwargs)

    def to_representation(self, data):
        """
        List of object instances -> List of dicts of primitive datatypes.
        """

        types_to_serializers = {
            "gene": self.gene_serializer,
            "str": self.str_serializer,
            "region": self.region_serializer,
        }

        return [
            types_to_serializers[item.entity_type].to_representation(item)
            for item in data
        ]


class EntitySerializer(serializers.BaseSerializer):
    class Meta:
        list_serializer_class = EntitiesListSerializer
