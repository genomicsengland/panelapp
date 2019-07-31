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
from django.test import TestCase
from django.urls import reverse_lazy
from accounts.tests.setup import LoginExternalUser
from panels.models import GenePanel
from panels.tests.factories import GenePanelSnapshotFactory
from panels.tests.factories import GenePanelEntrySnapshotFactory
from panels.tests.factories import STRFactory
from panels.tests.factories import RegionFactory
from panels.tests.factories import PanelTypeFactory


class TestAPIV1(LoginExternalUser):
    def setUp(self):
        super().setUp()
        self.gps = GenePanelSnapshotFactory(panel__status=GenePanel.STATUS.public)
        self.gps_public = GenePanelSnapshotFactory(
            panel__status=GenePanel.STATUS.public
        )
        self.gpes = GenePanelEntrySnapshotFactory(panel=self.gps_public)
        self.gpes_internal = GenePanelEntrySnapshotFactory(
            panel__panel__status=GenePanel.STATUS.internal
        )
        self.gpes_retired = GenePanelEntrySnapshotFactory(
            panel__panel__status=GenePanel.STATUS.retired
        )
        self.gpes_deleted = GenePanelEntrySnapshotFactory(
            panel__panel__status=GenePanel.STATUS.deleted
        )
        self.genes = GenePanelEntrySnapshotFactory.create_batch(4, panel=self.gps)
        self.str = STRFactory(
            panel__panel__status=GenePanel.STATUS.public, panel=self.gps
        )
        STRFactory(panel__panel__status=GenePanel.STATUS.public)
        self.region = RegionFactory(
            panel__panel__status=GenePanel.STATUS.public, panel=self.gps
        )
        RegionFactory(panel__panel__status=GenePanel.STATUS.public)

    def test_list_panels(self):
        r = self.client.get(reverse_lazy("api:v1:panels-list"))
        self.assertEqual(r.status_code, 200)

    def test_read_only_list_of_panels(self):
        r = self.client.post(
            reverse_lazy("api:v1:panels-list"), {"something": "something"}
        )
        self.assertEqual(r.status_code, 405)

    def test_list_panels_name(self):
        url = reverse_lazy("api:v1:panels-list")
        r = self.client.get(url)
        self.assertEqual(len(r.json()["results"]), 4)
        self.assertEqual(r.status_code, 200)

    def test_list_panels_filter_types(self):
        panel_type = PanelTypeFactory()
        self.gps.panel.types.add(panel_type)
        url = reverse_lazy("api:v1:panels-list") + "?type=" + panel_type.slug
        r = self.client.get(url)
        json_res = r.json()["results"]
        self.assertEqual(json_res[0]["types"][0]["name"], panel_type.name)
        self.assertEqual(r.status_code, 200)

    def test_retired_panels(self):
        url = reverse_lazy("api:v1:panels-list")

        self.gps.panel.status = GenePanel.STATUS.deleted
        self.gps.panel.save()

        r = self.client.get(url)
        self.assertEqual(len(r.json()["results"]), 3)
        self.assertEqual(r.status_code, 200)

        # Test deleted panels
        url = reverse_lazy("api:v1:panels-list")
        r = self.client.get("{}?retired=True".format(url))
        self.assertEqual(
            len(r.json()["results"]), 4
        )  # one for gpes via factory, 2nd - retired
        self.assertEqual(r.status_code, 200)

        # Test for unapproved panels
        self.gps_public.panel.status = GenePanel.STATUS.internal
        self.gps_public.panel.save()

        url = reverse_lazy("api:v1:panels-list")
        r = self.client.get("{}?retired=True".format(url))
        self.assertEqual(
            len(r.json()["results"]), 3
        )  # only retired panel will be visible
        self.assertEqual(r.status_code, 200)

    def test_internal_panel(self):
        self.gps.panel.status = GenePanel.STATUS.internal
        self.gps.panel.save()
        url = reverse_lazy("api:v1:panels-detail", args=(self.gps.panel.pk,))
        r = self.client.get(url)
        self.assertEqual(r.status_code, 404)
        self.assertEqual(r.json(), {"detail": "Not found."})

        new_version = self.gps.increment_version()
        self.gps.panel.active_panel.increment_version()
        r = self.client.get("{}?version=0.1".format(url))
        self.assertEqual(r.status_code, 200)

    def test_get_panel_name(self):
        r = self.client.get(
            reverse_lazy("api:v1:panels-detail", args=(self.gpes.panel.panel.name,))
        )
        self.assertEqual(r.status_code, 200)

    def test_get_panel_name_deleted(self):
        r = self.client.get(
            reverse_lazy(
                "api:v1:panels-detail", args=(self.gpes_deleted.panel.panel.name,)
            )
        )
        self.assertEqual(r.status_code, 404)
        self.assertEqual(r.json(), {"detail": "Not found."})

    def test_get_panel_internal(self):
        r = self.client.get(
            reverse_lazy(
                "api:v1:panels-detail", args=(self.gpes_internal.panel.panel.name,)
            )
        )
        self.assertEqual(r.status_code, 404)
        self.assertEqual(r.json(), {"detail": "Not found."})

    def test_get_panel_retired(self):
        r = self.client.get(
            reverse_lazy(
                "api:v1:panels-detail", args=(self.gpes_retired.panel.panel.name,)
            )
        )
        self.assertEqual(r.status_code, 404)
        self.assertEqual(r.json(), {"detail": "Not found."})

    def test_get_panel_pk(self):
        r = self.client.get(
            reverse_lazy("api:v1:panels-detail", args=(self.gpes.panel.panel.pk,))
        )
        self.assertEqual(r.status_code, 200)

    def test_get_panel_old_pk(self):
        r = self.client.get(
            reverse_lazy("api:v1:panels-detail", args=(self.gpes.panel.panel.old_pk,))
        )
        self.assertEqual(r.status_code, 200)

    def test_get_panel_version(self):
        self.gpes.panel.increment_version()
        self.gpes.panel.panel.active_panel.increment_version()

        url = reverse_lazy("api:v1:panels-detail", args=(self.gpes.panel.panel.pk,))
        r = self.client.get("{}?version=0.1".format(url))
        self.assertEqual(r.status_code, 200)

        self.gps.panel.status = GenePanel.STATUS.retired
        self.gps.panel.save()

        url = reverse_lazy("api:v1:panels-detail", args=(self.gpes.panel.panel.pk,))
        r = self.client.get("{}?version=0.1".format(url))
        self.assertEqual(r.status_code, 200)
        self.assertTrue(b"Query Error" not in r.content)

    def test_panel_created_timestamp(self):
        self.gpes.panel.increment_version()
        url = reverse_lazy("api:v1:panels-list")
        res = self.client.get(url)
        # find gps panel
        title = self.gps_public.level4title.name
        current_time = (
            str(self.gps_public.created).replace("+00:00", "Z").replace(" ", "T")
        )
        gps_panel = [r for r in res.json()["results"] if r["name"] == title][0]
        self.assertEqual(gps_panel["version_created"], current_time)

        r = self.client.get(
            reverse_lazy("api:v1:panels-detail", args=(gps_panel["id"],))
        ).json()
        self.assertEqual(r["version_created"], current_time)

    def test_get_search_gene(self):
        url = reverse_lazy(
            "api:v1:genes-detail", args=(self.gpes.gene_core.gene_symbol,)
        )
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)

    def test_search_by_gene(self):
        url = reverse_lazy(
            "api:v1:genes-detail", args=(self.gpes.gene_core.gene_symbol,)
        )
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)

        r = self.client.get(
            "{}?panel_name={}".format(url, self.gps_public.level4title.name)
        )
        self.assertEqual(r.status_code, 200)

        multi_genes_arg = "{},{}".format(
            self.genes[0].gene_core.gene_symbol, self.genes[1].gene_core.gene_symbol
        )
        multi_genes_url = reverse_lazy("api:v1:genes-detail", args=(multi_genes_arg,))
        r = self.client.get(multi_genes_url)
        self.assertEqual(r.status_code, 200)

    def test_strs_in_panel(self):
        r = self.client.get(
            reverse_lazy("api:v1:panels-detail", args=(self.str.panel.panel.pk,))
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["strs"][0]["entity_name"], self.str.name)
        self.assertEqual(
            r.json()["strs"][0]["grch37_coordinates"],
            [self.str.position_37.lower, self.str.position_37.upper],
        )
        self.assertEqual(
            r.json()["strs"][0]["grch38_coordinates"],
            [self.str.position_38.lower, self.str.position_38.upper],
        )
        self.assertEqual(
            r.json()["strs"][0]["pathogenic_repeats"], self.str.pathogenic_repeats
        )

    def test_genes_in_panel(self):
        r = self.client.get(
            reverse_lazy("api:v1:panels-detail", args=(self.gpes.panel.panel.pk,))
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(
            r.json()["genes"][0]["entity_name"], self.gpes.gene.get("gene_symbol")
        )
        self.assertEqual(
            r.json()["genes"][0]["mode_of_pathogenicity"],
            self.gpes.mode_of_pathogenicity,
        )

    def test_genes_in_panel_version(self):
        gene_symbol = self.gpes.gene.get("gene_symbol")
        self.gps_public.delete_gene(gene_symbol)
        self.gps_public = self.gps_public.panel.active_panel

        r = self.client.get(
            reverse_lazy("api:v1:panels-detail", args=(self.gpes.panel.panel.pk,))
            + "?version=0.0"
        )
        j = r.json()
        self.assertEqual(r.status_code, 200)
        gene_symbols_v0 = [g["entity_name"] for g in j["genes"]]
        self.assertTrue(gene_symbols_v0, gene_symbol)

        r = self.client.get(
            reverse_lazy("api:v1:panels-detail", args=(self.gpes.panel.panel.pk,))
        )
        j = r.json()
        self.assertEqual(r.status_code, 200)
        gene_symbols_v0 = [g["entity_name"] for g in j["genes"]]
        self.assertFalse(gene_symbols_v0, gene_symbol)

    def test_panel_exclude_entities(self):
        r = self.client.get(
            reverse_lazy("api:v1:panels-detail", args=(self.gpes.panel.panel.pk,))
            + "?exclude_entities=True"
        )
        j = r.json()
        self.assertEqual(r.status_code, 200)
        self.assertEqual(j.get("genes"), None)

        r = self.client.get(
            reverse_lazy("api:v1:panels-detail", args=(self.gpes.panel.panel.pk,))
            + "?exclude_entities=False"
        )
        j = r.json()
        self.assertEqual(r.status_code, 200)
        self.assertNotEqual(j.get("genes"), None)

    def test_green_genes_panel(self):
        # get all genes and their confidence levels counts
        r = self.client.get(
            reverse_lazy("api:v1:panels_genes-list", args=(self.gps.panel_id,))
            + "?confidence_level=3"
        )
        j = r.json()
        green_db = [e for e in self.gps.get_all_genes if e.saved_gel_status >= 3]
        green_api = [e for e in j["results"] if int(e.get("confidence_level")) >= 3]
        self.assertEqual(len(green_db), len(green_api))

        r = self.client.get(
            reverse_lazy("api:v1:panels_genes-list", args=(self.gps.panel_id,))
            + "?confidence_level=2"
        )
        j = r.json()
        amber_db = [e for e in self.gps.get_all_genes if e.saved_gel_status == 2]
        amber_api = [e for e in j["results"] if int(e.get("confidence_level")) == 2]
        self.assertEqual(len(amber_db), len(amber_api))

        r = self.client.get(
            reverse_lazy("api:v1:panels_genes-list", args=(self.gps.panel_id,))
            + "?confidence_level=1"
        )
        j = r.json()
        red_db = [e for e in self.gps.get_all_genes if e.saved_gel_status == 1]
        red_api = [e for e in j["results"] if int(e.get("confidence_level")) == 1]
        self.assertEqual(len(red_db), len(red_api))

    def test_genes_endpoint_in_panel_version(self):
        gene_symbol = self.gpes.gene.get("gene_symbol")
        self.gps_public.delete_gene(gene_symbol)
        self.gps_public = self.gps_public.panel.active_panel

        r = self.client.get(
            reverse_lazy("api:v1:panels_genes-list", args=(self.gpes.panel.panel.pk,))
            + "?version=0.0"
        )
        j = r.json()
        self.assertEqual(r.status_code, 200)
        gene_symbols_v0 = [g["entity_name"] for g in j["results"]]
        self.assertIn(gene_symbol, gene_symbols_v0)
        r = self.client.get(
            reverse_lazy("api:v1:panels_genes-list", args=(self.gpes.panel.panel.pk,))
        )
        j = r.json()
        self.assertEqual(r.status_code, 200)
        gene_symbols_v1 = [g["entity_name"] for g in j["results"]]
        self.assertNotIn(gene_symbol, gene_symbols_v1)

    def test_genes_endpoint_in_panel_version_old_pk(self):
        gene_symbol = self.gpes.gene.get("gene_symbol")
        self.gps_public.delete_gene(gene_symbol)
        self.gps_public = self.gps_public.panel.active_panel

        r = self.client.get(
            reverse_lazy("api:v1:panels_genes-list", args=(self.gpes.panel.panel.old_pk,))
            + "?version=0.0"
        )
        j = r.json()
        self.assertEqual(r.status_code, 200)
        gene_symbols_v0 = [g["entity_name"] for g in j["results"]]
        self.assertIn(gene_symbol, gene_symbols_v0)
        r = self.client.get(
            reverse_lazy("api:v1:panels_genes-list", args=(self.gpes.panel.panel.old_pk,))
        )
        j = r.json()
        self.assertEqual(r.status_code, 200)
        gene_symbols_v1 = [g["entity_name"] for g in j["results"]]
        self.assertNotIn(gene_symbol, gene_symbols_v1)

    def test_regions_endpoint_in_panel_version_old_panel_pk(self):
        name = self.region.name
        self.gps.delete_region(name)

        r = self.client.get(
            reverse_lazy("api:v1:panels-regions-list", args=(self.region.panel.panel.old_pk, ))
            + "?version=0.0"
        )
        j = r.json()
        self.assertEqual(r.status_code, 200)

    def test_regions_endpoint_in_panel_version(self):
        name = self.region.name
        self.gps.delete_region(name)

        r = self.client.get(
            reverse_lazy("api:v1:panels-regions-list", args=(self.region.panel.panel.pk, ))
            + "?version=0.0"
        )
        j = r.json()
        self.assertEqual(r.status_code, 200)
        names_v0 = [g["entity_name"] for g in j["results"]]
        self.assertIn(name, names_v0)
        r = self.client.get(
            reverse_lazy("api:v1:panels-regions-list", args=(self.region.panel.panel.pk, ))
            + "?version=0.1"
        )
        j = r.json()
        self.assertEqual(r.status_code, 200)
        names_v1 = [g["entity_name"] for g in j["results"]]
        self.assertNotIn(name, names_v1)

    def test_entities_pagination_historical_version(self):
        with self.settings(REST_FRAMEWORK={"PAGE_SIZE": 1, "DEFAULT_VERSIONING_CLASS": "rest_framework.versioning.NamespaceVersioning",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "DEFAULT_FILTER_BACKENDS": ("django_filters.rest_framework.DjangoFilterBackend",),
    "DEFAULT_VERSION": "v1",
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.TokenAuthentication",
    )}):
            self.gpes.panel.increment_version()
            r = self.client.get(reverse_lazy("api:v1:panels_genes-list", args=(self.gpes.panel.panel.pk,)) + "?version=0.0")
            self.assertEqual(r.status_code, 200)
            self.assertEqual(len(r.json()["results"]), 1)

    def test_filter_entities_list_historical(self):
        self.gps.panel.active_panel.increment_version()
        r = self.client.get(reverse_lazy("api:v1:panels_genes-list", args=(self.gps.panel_id,)) +
                            "?version=0.0&entity_name=" + self.gps.get_all_genes[0].gene.get("gene_symbol"))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()["results"]), 1)

    def test_genes_endpoint_entities_name(self):
        gene_symbol1 = self.genes[0].gene.get("gene_symbol")
        gene_symbol2 = self.genes[1].gene.get("gene_symbol")
        r = self.client.get(
            reverse_lazy("api:v1:panels_genes-list", args=(self.gps.panel_id,))
            + "?entity_name={},{}".format(gene_symbol1, gene_symbol2)
        )
        j = r.json()
        self.assertEqual(r.status_code, 200)
        gene_symbols = [g["entity_name"] for g in j["results"]]
        self.assertTrue(len(j["results"]), 2)
        self.assertTrue(gene_symbol1 in gene_symbols)
        self.assertTrue(gene_symbol2 in gene_symbols)

    def test_region_in_panel(self):
        r = self.client.get(
            reverse_lazy("api:v1:panels-detail", args=(self.region.panel.panel.pk,))
        )
        self.assertEqual(r.status_code, 200)
        region = r.json()["regions"][0]
        self.assertEqual(region["entity_name"], self.region.name)
        self.assertEqual(
            region["grch37_coordinates"],
            [self.region.position_37.lower, self.region.position_37.upper],
        )
        self.assertEqual(
            region["grch38_coordinates"],
            [self.region.position_38.lower, self.region.position_38.upper],
        )
        self.assertEqual(
            region["triplosensitivity_score"], self.region.triplosensitivity_score
        )

    def test_super_panel(self):
        super_panel = GenePanelSnapshotFactory(panel__status=GenePanel.STATUS.public)
        super_panel.child_panels.set([self.gps_public])

        r_direct = self.client.get(
            reverse_lazy("api:v1:panels-detail", args=(self.gps_public.panel.pk,))
        )
        result_genes = list(
            sorted(r_direct.json()["genes"], key=lambda x: x.get("gene_symbol"))
        )

        r = self.client.get(
            reverse_lazy("api:v1:panels-detail", args=(super_panel.panel.pk,))
        )
        self.assertEqual(r.status_code, 200)

        for gene in r.json()["genes"]:
            del gene["panel"]

        self.assertEqual(
            result_genes,
            list(sorted(r.json()["genes"], key=lambda x: x.get("gene_symbol"))),
        )

    def test_evaluations(self):
        r = self.client.get(
            reverse_lazy(
                "api:v1:genes-evaluations-list",
                args=(self.gpes.panel.panel.pk, self.gpes.gene_core.gene_symbol),
            )
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()["results"]), 4)

    def test_region_evaluations(self):
        r = self.client.get(
            reverse_lazy(
                "api:v1:regions-evaluations-list",
                args=(self.region.panel.panel.pk, self.region.name),
            )
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()["results"]), 4)

    def test_genes_list(self):
        r = self.client.get(reverse_lazy("api:v1:genes-list"))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()["results"]), 5)

    def test_genes_list_filter_types(self):
        panel_type = PanelTypeFactory()
        self.gps.panel.types.add(panel_type)
        r = self.client.get(
            reverse_lazy("api:v1:genes-list") + "?type=" + panel_type.slug
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()["results"]), 4)

    def test_genes_list_filter_name(self):
        r = self.client.get(
            reverse_lazy("api:v1:genes-detail", args=(self.gpes.gene_core.gene_symbol,))
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()["results"]), 1)

    def test_strs_list(self):
        r = self.client.get(reverse_lazy("api:v1:strs-list"))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()["results"]), 2)

    def test_strs_list_filter_types(self):
        panel_type = PanelTypeFactory()
        self.gps.panel.types.add(panel_type)
        r = self.client.get(
            reverse_lazy("api:v1:strs-list") + "?type=" + panel_type.slug
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()["results"]), 1)

    def test_strs_endpoint_in_panel_version_old_panel_pk(self):
        name = self.str.name
        self.gps.delete_str(name)

        r = self.client.get(
            reverse_lazy("api:v1:panels-strs-list", args=(self.str.panel.panel.old_pk, ))
            + "?version=0.0"
        )
        j = r.json()
        self.assertEqual(r.status_code, 200)

    def test_strs_endpoint_in_panel_version(self):
        name = self.str.name
        deleted = self.gps.delete_str(name)
        self.assertTrue(deleted)

        r = self.client.get(
            reverse_lazy("api:v1:panels-strs-list", args=(self.str.panel.panel.pk, ))
            + "?version=0.0"
        )
        j = r.json()
        self.assertEqual(r.status_code, 200)
        names_v0 = [g["entity_name"] for g in j["results"]]
        self.assertIn(name, names_v0)
        r = self.client.get(
            reverse_lazy("api:v1:panels-strs-list", args=(self.str.panel.panel.pk, ))
            + "?version=0.1"
        )
        j = r.json()
        self.assertEqual(r.status_code, 200)
        names_v1 = [g["entity_name"] for g in j["results"]]
        self.assertNotIn(name, names_v1)

    def test_regions_list(self):
        r = self.client.get(reverse_lazy("api:v1:regions-list"))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()["results"]), 2)

    def test_regions_list_filter_types(self):
        panel_type = PanelTypeFactory()
        self.gps.panel.types.add(panel_type)
        r = self.client.get(
            reverse_lazy("api:v1:regions-list") + "?type=" + panel_type.slug
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()["results"]), 1)

    def test_entities_list(self):
        r = self.client.get(reverse_lazy("api:v1:entities-list"))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()["results"]), 9)

    def test_read_only_list_of_entities(self):
        r = self.client.post(
            reverse_lazy("api:v1:entities-list"), {"something": "something"}
        )
        self.assertEqual(r.status_code, 405)

    def test_entities_list_filter_name(self):
        r = self.client.get(
            reverse_lazy("api:v1:entities-detail", args=(self.region.name,))
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()["results"]), 1)

    def test_entities_list_filter_types(self):
        panel_type = PanelTypeFactory()
        self.gps.panel.types.add(panel_type)
        url = reverse_lazy("api:v1:entities-list") + "?type=" + panel_type.slug
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()["results"]), 6)


class NonAuthAPIv1Request(TestCase):
    def setUp(self):
        super().setUp()
        self.gps = GenePanelSnapshotFactory(panel__status=GenePanel.STATUS.public)
        self.gps_public = GenePanelSnapshotFactory(
            panel__status=GenePanel.STATUS.public
        )
        self.gpes = GenePanelEntrySnapshotFactory(panel=self.gps_public)
        self.gpes_internal = GenePanelEntrySnapshotFactory(
            panel__panel__status=GenePanel.STATUS.internal
        )
        self.gpes_retired = GenePanelEntrySnapshotFactory(
            panel__panel__status=GenePanel.STATUS.retired
        )
        self.gpes_deleted = GenePanelEntrySnapshotFactory(
            panel__panel__status=GenePanel.STATUS.deleted
        )
        self.genes = GenePanelEntrySnapshotFactory.create_batch(4, panel=self.gps)
        self.str = STRFactory(panel__panel__status=GenePanel.STATUS.public)
        self.region = RegionFactory(panel__panel__status=GenePanel.STATUS.public)

    def test_list_of_panels(self):
        r = self.client.get(reverse_lazy("api:v1:panels-list"))
        self.assertEqual(r.status_code, 200)

    def test_read_only_list_of_panels(self):
        r = self.client.post(
            reverse_lazy("api:v1:panels-list"), {"something": "something"}
        )
        self.assertEqual(r.status_code, 403)

    def test_read_only_list_of_entities(self):
        r = self.client.post(
            reverse_lazy("api:v1:entities-list"), {"something": "something"}
        )
        self.assertEqual(r.status_code, 403)

    def test_get_panel_name(self):
        r = self.client.get(
            reverse_lazy("api:v1:panels-detail", args=(self.gpes.panel.panel.name,))
        )
        self.assertEqual(r.status_code, 200)

    def test_get_search_gene(self):
        url = reverse_lazy(
            "api:v1:genes-detail", args=(self.gpes.gene_core.gene_symbol,)
        )
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)

    def test_region_search(self):
        url = reverse_lazy("api:v1:regions-detail", args=(self.region.name,))
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)

    def test_evaluations(self):
        r = self.client.get(
            reverse_lazy(
                "api:v1:genes-evaluations-list",
                args=(self.gpes.panel.panel.pk, self.gpes.gene_core.gene_symbol),
            )
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()["results"]), 4)

    def test_genes_evaluations_old_version(self):
        """We don't have evaluations for old versions,
        they are only saved on the current version

        :return:
        """
        gene_symbol = self.gpes.gene_core.gene_symbol
        self.gpes.panel.delete_gene(gene_symbol)

        r = self.client.get(
            reverse_lazy(
                "api:v1:strs-evaluations-list",
                args=(self.gpes.panel.panel.pk, gene_symbol),
            ) + "?version=0.0"
        )
        self.assertEqual(r.status_code, 400)

    def test_strs_evaluations(self):
        r = self.client.get(
            reverse_lazy(
                "api:v1:strs-evaluations-list",
                args=(self.str.panel.panel.pk, self.str.name),
            )
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()["results"]), 4)

    def test_strs_evaluations_old_version(self):
        """We don't have evaluations for old versions,
        they are only saved on the current version

        :return:
        """
        name = self.str.name
        self.str.panel.delete_str(name)

        r = self.client.get(
            reverse_lazy(
                "api:v1:strs-evaluations-list",
                args=(self.str.panel.panel.pk, self.str.name),
            ) + "?version=0.0"
        )
        self.assertEqual(r.status_code, 400)

    def test_region_evaluations(self):
        r = self.client.get(
            reverse_lazy(
                "api:v1:regions-evaluations-list",
                args=(self.region.panel.panel.pk, self.region.name),
            )
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()["results"]), 4)

    def test_region_evaluations_old_version(self):
        """We don't have evaluations for old versions,
        they are only saved on the current version

        :return:
        """
        name = self.region.name
        self.region.panel.delete_region(name)

        r = self.client.get(
            reverse_lazy(
                "api:v1:regions-evaluations-list",
                args=(self.region.panel.panel.pk, self.region.name),
            ) + "?version=0.0"
        )
        self.assertEqual(r.status_code, 400)
