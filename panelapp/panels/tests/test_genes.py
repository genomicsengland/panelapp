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
import json
import os
from datetime import datetime
from datetime import date
from django.urls import reverse_lazy
from faker import Factory
from accounts.tests.setup import LoginGELUser
from panels.models.import_tools import update_gene_collection
from panels.models import Gene

from panels.models import GenePanel
from panels.models import GenePanelSnapshot
from panels.models import STR
from panels.models import Region
from panels.models import GenePanelEntrySnapshot
from panels.models import HistoricalSnapshot
from panels.tests.factories import GeneFactory
from panels.tests.factories import GenePanelSnapshotFactory
from panels.tests.factories import GenePanelEntrySnapshotFactory
from panels.tests.factories import STRFactory
from panels.tests.factories import RegionFactory


fake = Factory.create()


class GeneTest(LoginGELUser):
    "Test gene import"

    def test_import_gene(self):
        """
        Test Gene import.
        """

        file_path = os.path.join(os.path.dirname(__file__), "test_import.json")
        test_gene_file = os.path.abspath(file_path)

        # Create genes to update
        update_symbol = []
        update = []
        with open(test_gene_file) as f:
            results = json.load(f)
            for r in results["update"]:
                update.append(GeneFactory(gene_symbol=r["gene_symbol"]).gene_symbol)
            for r in results["update_symbol"]:
                update_symbol.append(GeneFactory(gene_symbol=r[1]).gene_symbol)

        with open(test_gene_file) as f:
            url = reverse_lazy("panels:upload_genes")
            self.client.post(url, {"gene_list": f})

        for us in update_symbol:
            self.assertFalse(Gene.objects.get(gene_symbol=us).active)
        for u in update:
            gene = Gene.objects.get(gene_symbol=u)
            if gene.ensembl_genes:
                self.assertTrue(gene.active)
            else:
                self.assertFalse(gene.active)

    def test_gene_from_json(self):
        gene_dict_file = os.path.join(os.path.dirname(__file__), "gene_dict.json")
        with open(gene_dict_file) as f:
            dictionary = json.load(f)
            g = Gene.from_dict(dictionary=dictionary)
            dictionary["hgnc_date_symbol_changed"] = date(2004, 10, 15)
            dictionary["hgnc_release"] = datetime(2017, 7, 21, 0, 0)
            self.assertEqual(dictionary, g.dict_tr())

    def test_download_genes(self):
        gps = GenePanelSnapshotFactory()
        GenePanelEntrySnapshotFactory.create_batch(2, panel=gps)

        res = self.client.get(reverse_lazy("panels:download_genes"))
        self.assertEqual(res.status_code, 200)

    def test_list_genes(self):
        GenePanelEntrySnapshotFactory.create_batch(3)
        r = self.client.get(reverse_lazy("panels:entities_list"))
        self.assertEqual(r.status_code, 200)

    def test_gene_not_ready(self):
        gpes = GenePanelEntrySnapshotFactory()
        url = reverse_lazy(
            "panels:mark_entity_as_not_ready",
            args=(gpes.panel.panel.pk, "gene", gpes.gene.get("gene_symbol")),
        )
        r = self.client.post(url, {})
        self.assertEqual(r.status_code, 302)

    def test_update_gene_collection(self):
        gene_to_update = GeneFactory()
        gene_to_delete = GeneFactory()
        gene_to_update_symbol = GeneFactory()

        gps = GenePanelSnapshotFactory()
        GenePanelEntrySnapshotFactory.create_batch(2, panel=gps)  # random genes
        GenePanelEntrySnapshotFactory.create(gene_core=gene_to_update, panel=gps)
        STRFactory.create_batch(2, panel=gps)  # random STRs
        STRFactory.create(gene_core=gene_to_update, panel=gps)
        RegionFactory.create_batch(2, panel=gps)  # random STRs
        RegionFactory.create(gene_core=gene_to_update, panel=gps)

        gps = GenePanelSnapshotFactory()
        GenePanelEntrySnapshotFactory.create_batch(2, panel=gps)  # random genes
        STRFactory.create_batch(2, panel=gps)  # random STRs
        GenePanelEntrySnapshotFactory.create(gene_core=gene_to_update_symbol, panel=gps)
        STRFactory.create(gene_core=gene_to_update_symbol, panel=gps)
        RegionFactory.create_batch(2, panel=gps)  # random STRs
        RegionFactory.create(gene_core=gene_to_update_symbol, panel=gps)

        to_insert = [
            Gene(gene_symbol="A", ensembl_genes={"inserted": True}).dict_tr(),
            Gene(gene_symbol="B", ensembl_genes={"inserted": True}).dict_tr(),
        ]

        to_update = [
            Gene(
                gene_symbol=gene_to_update.gene_symbol, ensembl_genes={"updated": True}
            ).dict_tr()
        ]

        to_update_symbol = [
            (
                Gene(gene_symbol="C", ensembl_genes={"updated": True}).dict_tr(),
                gene_to_update_symbol.gene_symbol,
            )
        ]

        to_delete = [gene_to_delete.gene_symbol]

        migration = {
            "insert": to_insert,
            "update": to_update,
            "delete": to_delete,
            "update_symbol": to_update_symbol,
        }

        update_gene_collection(migration)

        self.assertTrue(
            GenePanelEntrySnapshot.objects.get_active()
            .get(gene_core__gene_symbol=gene_to_update.gene_symbol)
            .gene.get("ensembl_genes")["updated"]
        )

        self.assertTrue(
            STR.objects.get_active()
            .get(gene_core__gene_symbol=gene_to_update.gene_symbol)
            .gene.get("ensembl_genes")["updated"]
        )

        self.assertTrue(
            Region.objects.get_active()
            .get(gene_core__gene_symbol=gene_to_update.gene_symbol)
            .gene.get("ensembl_genes")["updated"]
        )

        updated_not_updated = [
            gpes.gene["ensembl_genes"]
            for gpes in GenePanelEntrySnapshot.objects.filter(
                gene_core__gene_symbol=gene_to_update.gene_symbol
            )
        ]
        not_updated = HistoricalSnapshot.objects.all()[1].data['genes'][0]['gene_data']['ensembl_genes']
        self.assertNotEqual(updated_not_updated[0], not_updated)

        updated_not_updated = [
            str_item.gene["ensembl_genes"]
            for str_item in STR.objects.filter(
                gene_core__gene_symbol=gene_to_update.gene_symbol
            )
        ]
        not_updated = HistoricalSnapshot.objects.all()[1].data['strs'][0]['gene_data']['ensembl_genes']

        self.assertNotEqual(updated_not_updated[0], not_updated)

        updated_not_updated = [
            region_item.gene["ensembl_genes"]
            for region_item in Region.objects.filter(
                gene_core__gene_symbol=gene_to_update.gene_symbol
            )
        ]
        not_updated = HistoricalSnapshot.objects.all()[1].data['regions'][0]['gene_data']['ensembl_genes']

        self.assertNotEqual(updated_not_updated[0], not_updated)

        self.assertFalse(
            Gene.objects.get(gene_symbol=gene_to_update_symbol.gene_symbol).active
        )
        self.assertFalse(
            Gene.objects.get(gene_symbol=gene_to_delete.gene_symbol).active
        )
        self.assertTrue(Gene.objects.get(gene_symbol="A").active)

        self.assertTrue(
            GenePanelEntrySnapshot.objects.get(gene_core__gene_symbol="C").gene.get(
                "ensembl_genes"
            )["updated"]
        )

        self.assertTrue(
            STR.objects.get(gene_core__gene_symbol="C").gene.get("ensembl_genes")[
                "updated"
            ]
        )

        self.assertTrue(
            Region.objects.get(gene_core__gene_symbol="C").gene.get("ensembl_genes")[
                "updated"
            ]
        )

    def test_get_panels_for_a_gene(self):
        gene = GeneFactory()

        gps = GenePanelSnapshotFactory()
        GenePanelEntrySnapshotFactory.create_batch(2, panel=gps)  # random genes
        GenePanelEntrySnapshotFactory.create(gene_core=gene, panel=gps)

        gps = GenePanelSnapshotFactory()
        GenePanelEntrySnapshotFactory.create_batch(2, panel=gps)  # random genes
        GenePanelEntrySnapshotFactory.create(gene_core=gene, panel=gps)

        gps3 = GenePanelSnapshotFactory()
        GenePanelEntrySnapshotFactory.create_batch(2, panel=gps3)  # random genes
        GenePanelEntrySnapshotFactory.create(gene_core=gene, panel=gps3)

        gps4 = GenePanelSnapshotFactory()
        GenePanelEntrySnapshotFactory.create_batch(2, panel=gps4)  # random genes

        assert (
            GenePanelEntrySnapshot.objects.get_gene_panels(gene.gene_symbol).count()
            == 3
        )

        url = reverse_lazy("panels:entity_detail", kwargs={"slug": gene.gene_symbol})
        res = self.client.get(url)
        assert len(res.context_data["entries"]) == 3

    def test_get_internal_panels_for_a_gene(self):
        gene = GeneFactory()

        gps = GenePanelSnapshotFactory(panel__status=GenePanel.STATUS.public)
        GenePanelEntrySnapshotFactory.create_batch(2, panel=gps)  # random genes
        GenePanelEntrySnapshotFactory.create(gene_core=gene, panel=gps)

        gps2 = GenePanelSnapshotFactory(panel__status=GenePanel.STATUS.internal)
        GenePanelEntrySnapshotFactory.create_batch(2, panel=gps2)  # random genes
        GenePanelEntrySnapshotFactory.create(gene_core=gene, panel=gps2)

        gps3 = GenePanelSnapshotFactory(panel__status=GenePanel.STATUS.public)
        GenePanelEntrySnapshotFactory.create_batch(2, panel=gps3)  # random genes

        self.assertEqual(
            GenePanelEntrySnapshot.objects.get_gene_panels(gene.gene_symbol).count(), 2
        )
        self.assertEqual(
            GenePanelSnapshot.objects.get_gene_panels(gene.gene_symbol).count(), 1
        )
        self.assertEqual(
            GenePanelSnapshot.objects.get_gene_panels(
                gene.gene_symbol, all=True, internal=True
            ).count(),
            2,
        )

        url = reverse_lazy("panels:entity_detail", kwargs={"slug": gene.gene_symbol})
        res = self.client.get(url)
        self.assertEqual(len(res.context_data["entries"]), 2)
