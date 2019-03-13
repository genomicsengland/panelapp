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
import os
from django.core import mail
from django.test import Client
from django.urls import reverse_lazy
from faker import Factory
from django.test import TransactionTestCase, TestCase
from accounts.tests.setup import LoginGELUser
from panels.models import GenePanel
from panels.models import GenePanelEntrySnapshot
from panels.models import Region
from panels.models import STR
from panels.tasks import email_panel_promoted
from panels.tests.factories import GeneFactory
from panels.tests.factories import STRFactory
from panels.tests.factories import RegionFactory
from panels.tests.factories import EvidenceFactory
from panels.tests.factories import GenePanelSnapshotFactory
from panels.tests.factories import GenePanelEntrySnapshotFactory
from panels.tests.factories import PanelTypeFactory
from panels.management.commands.update_gene_ensembl import process

fake = Factory.create()


class CommandUpdateEnsemblTest(LoginGELUser):
    def setUp(self):
        super().setUp()

    def test_update_ensembl(self):
        gene_symbol = "FAM58A"
        gene_to_update = GeneFactory(gene_symbol=gene_symbol)
        ensembl_data = {
            "GRch37": {
                "82": {
                    "ensembl_id": "ENSG00000147382",
                    "location": "X:152853377-152865500",
                }
            },
            "GRch38": {
                "90": {
                    "ensembl_id": "ENSG00000262919",
                    "location": "X:153587919-153600045",
                }
            },
        }
        json_data = {gene_symbol: ensembl_data}

        gps = GenePanelSnapshotFactory()
        GenePanelEntrySnapshotFactory.create_batch(2, panel=gps)  # random genes
        GenePanelEntrySnapshotFactory.create(gene_core=gene_to_update, panel=gps)
        STRFactory.create_batch(2, panel=gps)  # random STRs
        STRFactory.create(gene_core=gene_to_update, panel=gps)
        RegionFactory.create_batch(2, panel=gps)  # random STRs
        RegionFactory.create(gene_core=gene_to_update, panel=gps)

        gps_2 = GenePanelSnapshotFactory()
        GenePanelEntrySnapshotFactory.create_batch(2, panel=gps_2)  # random genes
        STRFactory.create_batch(2, panel=gps_2)  # random STRs
        RegionFactory.create_batch(2, panel=gps_2)  # random STRs
        RegionFactory.create(gene_core=gene_to_update, panel=gps_2)

        # make sure ensembl data doesn't match
        for gene in GenePanelEntrySnapshot.objects.filter(
            gene__gene_symbol=gene_symbol
        ):
            self.assertNotEqual(gene.gene.get("ensembl_genes"), ensembl_data)

        for str in STR.objects.filter(gene__gene_symbol=gene_symbol):
            self.assertNotEqual(gene.gene.get("ensembl_genes"), ensembl_data)

        for region in Region.objects.filter(gene__gene_symbol=gene_symbol):
            self.assertNotEqual(gene.gene.get("ensembl_genes"), ensembl_data)

        gps_pk = gps.pk
        gps_version = gps.version
        gps_2_version = gps_2.version

        process(json_data)

        # make sure previous data didn't change
        for gene in GenePanelEntrySnapshot.objects.filter(
            gene__gene_symbol=gene_symbol, panel_id=gps_pk
        ):
            self.assertNotEqual(gene.gene.get("ensembl_genes"), ensembl_data)

        for str in STR.objects.filter(gene__gene_symbol=gene_symbol, panel_id=gps_pk):
            self.assertNotEqual(gene.gene.get("ensembl_genes"), ensembl_data)

        for region in Region.objects.filter(
            gene__gene_symbol=gene_symbol, panel_id=gps_pk
        ):
            self.assertNotEqual(gene.gene.get("ensembl_genes"), ensembl_data)

        gps = gps.panel.active_panel
        gps_2 = gps_2.panel.active_panel

        self.assertNotEqual(gps_version, gps.version)
        self.assertNotEqual(gps_2_version, gps_2.version)

        # make sure new data has changed
        for gene in GenePanelEntrySnapshot.objects.filter(
            gene__gene_symbol=gene_symbol, panel=gps
        ):
            self.assertEqual(gene.gene.get("ensembl_genes"), ensembl_data)

        for str in STR.objects.filter(gene__gene_symbol=gene_symbol, panel=gps):
            self.assertEqual(gene.gene.get("ensembl_genes"), ensembl_data)

        for region in Region.objects.filter(gene__gene_symbol=gene_symbol, panel=gps):
            self.assertEqual(gene.gene.get("ensembl_genes"), ensembl_data)
