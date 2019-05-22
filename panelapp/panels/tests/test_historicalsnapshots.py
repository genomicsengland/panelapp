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
from django.urls import reverse_lazy
from django.test import Client
from faker import Factory
from random import choice
from accounts.tests.setup import LoginGELUser
from panels.models import GenePanelEntrySnapshot
from panels.models import Region
from panels.models import GenePanelSnapshot
from panels.models import Evidence
from panels.models import GenePanel
from panels.models import Evaluation
from panels.models import HistoricalSnapshot
from panels.tests.factories import GeneFactory
from panels.tests.factories import RegionFactory
from panels.tests.factories import GenePanelSnapshotFactory
from panels.tests.factories import GenePanelEntrySnapshotFactory
from panels.tests.factories import TagFactory
from panels.tests.factories import CommentFactory

fake = Factory.create()


class HistoricalSnapshotTest(LoginGELUser):

    def setUp(self):
        super().setUp()
        self.panel_data = self.create_panel_data()

    def create_panel_data(self):
        return {
            "level2": fake.sentence(nb_words=6, variable_nb_words=True),
            "level3": fake.sentence(nb_words=6, variable_nb_words=True),
            "level4": fake.sentence(nb_words=6, variable_nb_words=True),
            "description": fake.text(max_nb_chars=300),
            "omim": fake.sentences(nb=3),
            "orphanet": fake.sentences(nb=3),
            "hpo": fake.sentences(nb=3),
            "old_panels": fake.sentences(nb=3),
            "status": GenePanel.STATUS.internal,
        }

    def test_import_panel(self):
        gpes = GenePanelSnapshotFactory()
        GenePanelEntrySnapshotFactory.create_batch(2, panel=gpes)  # random genes
        snap = HistoricalSnapshot().import_panel(gpes)

        assert snap.data
        assert len(snap.data["genes"]) == 2
        assert snap.panel == gpes.panel
        assert snap.major_version == gpes.major_version
        assert snap.minor_version == gpes.minor_version

    def test_download_historical_snapshot_tsv(self):
        gps = GenePanelSnapshotFactory()

        HistoricalSnapshot().import_panel(gps)
        gps.increment_version()
        res = self.client.post(
            reverse_lazy("panels:download_old_panel_tsv", args=(gps.panel.pk,)), {"panel_version": "0.0"}
        )
        assert res.status_code == 200

    def test_legacy_api_retrieve_historical_snapshot(self):
        gps = GenePanelSnapshotFactory()
        GenePanelEntrySnapshotFactory.create_batch(2, panel=gps)  # random genes

        HistoricalSnapshot().import_panel(gps)

        res = self.client.get(
            reverse_lazy("webservices:get_panel", args=(gps.panel.pk,)), {"version": "0.0"}
        )

        assert res.status_code == 200
