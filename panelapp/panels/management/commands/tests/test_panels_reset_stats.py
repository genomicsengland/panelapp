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

from faker import Factory
from django.db import transaction
from accounts.tests.setup import LoginGELUser
from panels.models import GenePanelSnapshot
from panels.tests.factories import GeneFactory
from panels.tests.factories import STRFactory
from panels.tests.factories import RegionFactory
from panels.tests.factories import GenePanelSnapshotFactory
from panels.tests.factories import GenePanelEntrySnapshotFactory
from panels.management.commands.panels_reset_stats import command

fake = Factory.create()


class CommandResetPanelsStatsTest(LoginGELUser):
    def setUp(self):
        super().setUp()

    def test_reset_panels_stats(self):
        gene = GeneFactory()
        gps = GenePanelSnapshotFactory()
        GenePanelEntrySnapshotFactory.create_batch(2, panel=gps)  # random genes
        GenePanelEntrySnapshotFactory.create(gene_core=gene, panel=gps)
        STRFactory.create_batch(2, panel=gps)  # random STRs
        STRFactory.create(gene_core=gene, panel=gps)
        RegionFactory.create_batch(2, panel=gps)  # random regions
        RegionFactory.create(gene_core=gene, panel=gps)

        gps.stats = {}
        gps.save()

        gps2 = GenePanelSnapshotFactory()
        gps2.child_panels.add(gps)

        stats = gps.stats
        version = gps.version
        super_stats = gps2.stats
        super_version = gps2.version

        command()

        updated_gps = GenePanelSnapshot.objects.filter(panel_id=gps.panel_id).first()
        updated_gps2 = GenePanelSnapshot.objects.filter(panel_id=gps2.panel_id).first()

        self.assertNotEqual(version, updated_gps.version)
        self.assertNotEqual(stats, updated_gps.stats)

        self.assertNotEqual(super_version, updated_gps2.version)
        self.assertNotEqual(super_stats, updated_gps2.stats)