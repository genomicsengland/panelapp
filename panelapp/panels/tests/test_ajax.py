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
from django.urls import reverse_lazy
from accounts.tests.setup import LoginGELUser
from panels.tests.factories import GenePanelEntrySnapshotFactory
from panels.models import GenePanel
from panels.models import TrackRecord
from panels.models import Evidence


class AjaxGenePanelEntrySnapshotTest(LoginGELUser):
    gpes = None

    def setUp(self):
        super().setUp()
        self.gpes = GenePanelEntrySnapshotFactory()
        evidence = self.gpes.evidence.all()[0]

        evidence.reviewer.user_type = "GEL"
        evidence.reviewer.save()

    def helper_clear(self, content_type, additional_kwargs=None):
        kwargs = {
            "pk": self.gpes.panel.panel.pk,
            "entity_type": "gene",
            "entity_name": self.gpes.gene.get("gene_symbol"),
        }

        if additional_kwargs:
            kwargs.update(additional_kwargs)

        url = reverse_lazy("panels:{}".format(content_type), kwargs=kwargs)
        res = self.client.get(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        assert res.json().get("status") == 200

        gps = GenePanel.objects.get(pk=self.gpes.panel.panel.pk).active_panel
        gene = gps.get_gene(self.gpes.gene.get("gene_symbol"))
        assert gps.version != self.gpes.panel.version
        return res, gene

    def test_clear_phenotypes(self):
        res, gene = self.helper_clear("clear_entity_phenotypes")
        assert gene.phenotypes == []

    def test_clear_gene_publications(self):
        res, gene = self.helper_clear("clear_entity_publications")
        assert gene.publications == []

    def test_clear_gene_mode_of_pathogenicity(self):
        res, gene = self.helper_clear("clear_entity_mode_of_pathogenicity")
        assert gene.mode_of_pathogenicity == ""

    def test_clear_sources(self):
        res, gene = self.helper_clear("clear_entity_sources")
        assert gene.evidence.count() == 3

        self.assertTrue(
            gene.track.filter(issue_type=TrackRecord.ISSUE_TYPES.ClearSources).count()
            > 0
        )

    def test_clear_single_source(self):
        # clear all evidences
        self.gpes.evidence.all().delete()
        ev = Evidence.objects.create(
            name="UKGTN", reviewer=self.gel_user.reviewer, rating=3, comment="Test"
        )
        self.gpes.evidence.add(ev)
        ev = Evidence.objects.create(
            name="Expert Review Green",
            reviewer=self.gel_user.reviewer,
            rating=3,
            comment="Test",
        )
        self.gpes.evidence.add(ev)

        before_count = self.gpes.evidence.count()
        evidence_count = self.gpes.evidence.filter(name="UKGTN").count()
        res, gene = self.helper_clear(
            "clear_entity_source", additional_kwargs={"source": "UKGTN"}
        )
        assert gene.evidence.count() == before_count - evidence_count
        assert res.content.find(str.encode("UKGTN")) == -1

    def test_clear_single_source_expert_review(self):
        """When clearing the source if Expert Reviews is there is still should be the same"""

        self.gpes.evidence.all().delete()
        ev = Evidence.objects.create(
            name="UKGTN", reviewer=self.gel_user.reviewer, rating=3, comment="Test"
        )
        self.gpes.evidence.add(ev)
        ev = Evidence.objects.create(
            name="Expert Review Green",
            reviewer=self.gel_user.reviewer,
            rating=3,
            comment="Test",
        )
        self.gpes.evidence.add(ev)

        evidence = [
            ev
            for ev in self.gpes.evidence.all()
            if ev.is_GEL and not ev.name.startswith("Expert Review")
        ][0]
        before_count = self.gpes.evidence.count()
        evidence_count = self.gpes.evidence.filter(name="UKGTN").count()
        res, gene = self.helper_clear(
            "clear_entity_source", additional_kwargs={"source": "UKGTN"}
        )
        assert gene.evidence.count() == before_count - evidence_count
        assert res.content.find(str.encode("UKGTN")) == -1

        self.assertEqual(gene.status, Evidence.EXPERT_REVIEWS["Expert Review Green"])


class AjaxGenePanelEntryTest(LoginGELUser):
    gpes = None

    def setUp(self):
        super().setUp()
        self.gpes = GenePanelEntrySnapshotFactory()
        self.gpes2 = GenePanelEntrySnapshotFactory()

    def helper_panel(self, action):
        kwargs = {"pk": self.gpes.panel.panel.pk}
        url = reverse_lazy("panels:{}".format(action), kwargs=kwargs)
        res = self.client.get(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        assert res.json().get("status") == 200
        return res

    def test_delete_panel(self):
        pk = self.gpes.panel.panel.pk
        res = self.helper_panel("delete_panel")
        assert GenePanel.objects.filter(pk=pk).count() == 1
        self.assertEqual(GenePanel.objects.get(pk=pk).status, GenePanel.STATUS.deleted)
        assert res.content.find(str.encode(self.gpes2.panel.panel.name))

    def test_approve_panel(self):
        self.gpes.panel.panel.status = GenePanel.STATUS.internal
        self.gpes.panel.panel.save()

        self.helper_panel("approve_panel")
        assert (
            GenePanel.objects.get(pk=self.gpes.panel.panel.pk).status
            == GenePanel.STATUS.public
        )

    def test_reject_panel(self):
        self.gpes.panel.panel.status = GenePanel.STATUS.public
        self.gpes.panel.panel.save()

        self.helper_panel("reject_panel")
        assert (
            GenePanel.objects.get(pk=self.gpes.panel.panel.pk).status
            == GenePanel.STATUS.internal
        )
