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
from accounts.tests.setup import LoginGELUser
from panels.models import GenePanel
from panels.models import GenePanelEntrySnapshot
from panels.models import HistoricalSnapshot
from panels.tasks import email_panel_promoted
from panels.tests.factories import GeneFactory
from panels.tests.factories import STRFactory
from panels.tests.factories import EvidenceFactory
from panels.tests.factories import GenePanelSnapshotFactory
from panels.tests.factories import GenePanelEntrySnapshotFactory
from panels.tests.factories import PanelTypeFactory


fake = Factory.create()


class GenePanelTest(LoginGELUser):
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

    def test_create_unauthorised(self):
        c = Client()
        res = c.post(reverse_lazy("panels:create"), self.panel_data)
        assert res.status_code == 403

    def test_create_unauthorised_external_reviewer(self):
        c = Client()
        c.force_login(self.external_user)
        res = c.post(reverse_lazy("panels:create"), self.panel_data)
        assert res.status_code == 403

    def test_create_gel_reviewer(self):
        res = self.client.post(reverse_lazy("panels:create"), self.panel_data)
        assert res.status_code == 302

        gp = GenePanel.objects.get(name=self.panel_data["level4"])
        assert gp
        assert gp.active_panel.major_version == 0
        assert gp.active_panel.minor_version == 0

    def test_panel_index(self):
        GenePanelEntrySnapshotFactory.create_batch(4)
        r = self.client.get(reverse_lazy("panels:index"))
        self.assertEqual(r.status_code, 200)

    def test_view_add_gene_to_panel(self):
        gpes = GenePanelEntrySnapshotFactory()
        r = self.client.get(
            reverse_lazy("panels:add_entity", args=(gpes.panel.panel.pk, "gene"))
        )
        self.assertEqual(r.status_code, 200)

    def test_view_edit_gene_in_panel(self):
        gpes = GenePanelEntrySnapshotFactory()
        url = reverse_lazy(
            "panels:edit_entity",
            args=(gpes.panel.panel.pk, "gene", gpes.gene.get("gene_symbol")),
        )
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)

    def test_panel_detail_view(self):
        gps = GenePanelSnapshotFactory()
        c = Client()
        r = c.get(reverse_lazy("panels:detail", kwargs={"pk": gps.panel.pk}))

        assert r.status_code == 200

    def test_panel_check_internal_status_visible(self):
        gps = GenePanelSnapshotFactory()
        c = Client()
        r = c.get(reverse_lazy("panels:detail", kwargs={"pk": gps.panel.pk}))

        assert r.content.find(b"This Panel is marked as Internal") != -1

    def test_update_panel(self):
        gps = GenePanelSnapshotFactory()
        url = reverse_lazy("panels:update", kwargs={"pk": gps.panel.pk})
        data = self.create_panel_data()
        self.client.post(url, data)

        gp = GenePanel.objects.get(pk=gps.panel.pk)
        assert gp.active_panel.major_version == 0
        assert gp.active_panel.minor_version == 1
        assert gp.name == data["level4"]

    def test_update_status(self):
        gps = GenePanelSnapshotFactory()
        url = reverse_lazy("panels:update", kwargs={"pk": gps.panel.pk})
        data = self.create_panel_data()
        data["status"] = GenePanel.STATUS.public
        self.client.post(url, data)

        gp = GenePanel.objects.get(pk=gps.panel.pk)
        assert gp.status == data["status"]

    def test_update_panel_many_to_many(self):
        gpes = GenePanelEntrySnapshotFactory()
        url = reverse_lazy("panels:update", kwargs={"pk": gpes.panel.panel.pk})
        data = self.create_panel_data()
        self.client.post(url, data)

        gp = GenePanel.objects.get(pk=gpes.panel.panel.pk)

        active_snapshot = gp.active_panel
        assert active_snapshot.major_version == 0
        assert active_snapshot.minor_version == 1
        assert gp.name == data["level4"]
        assert active_snapshot.get_all_genes.count() == 1

    def test_mark_all_genes_not_ready(self):
        gps = GenePanelSnapshotFactory()
        GenePanelEntrySnapshotFactory.create_batch(5, ready=True, panel=gps)
        assert GenePanelEntrySnapshot.objects.filter(ready=True).count() == 5

        url = reverse_lazy("panels:mark_not_ready", kwargs={"pk": gps.panel.pk})
        res = self.client.get(url)
        assert GenePanelEntrySnapshot.objects.filter(ready=True).count() == 0
        assert res.status_code == 302

    def test_delete_gene(self):
        gps = GenePanelSnapshotFactory()
        genes = GenePanelEntrySnapshotFactory.create_batch(5, panel=gps)
        gene_symbol = genes[2].gene["gene_symbol"]

        number_of_genes = gps.stats.get("number_of_genes")

        assert gps.has_gene(gene_symbol) is True
        gps = gps.panel.active_panel
        gps.delete_gene(gene_symbol)
        gps = gps.panel.active_panel
        assert gps.panel.active_panel.has_gene(gene_symbol) is False
        assert number_of_genes - 1 == gps.panel.active_panel.stats.get(
            "number_of_genes"
        )  # 4 is due to create_batch

        old_gps = HistoricalSnapshot.objects.get(panel__pk=gps.panel.pk)
        assert (
            "{}.{}".format(old_gps.major_version, old_gps.minor_version) != gps.version
        )
        assert gene_symbol in [g["entity_name"] for g in old_gps.data["genes"]]

        new_gps = GenePanel.objects.get(pk=gps.panel.pk).active_panel
        assert new_gps.has_gene(gene_symbol) is False

        gene_symbol = genes[3].gene["gene_symbol"]
        assert new_gps.has_gene(gene_symbol) is True
        new_gps.delete_gene(gene_symbol, False)
        assert new_gps.has_gene(gene_symbol) is False

        new_gps = GenePanel.objects.get(pk=gps.panel.pk).active_panel
        assert new_gps.has_gene(gene_symbol) is False

    def test_delete_gene_ajax(self):
        gps = GenePanelSnapshotFactory()
        genes = GenePanelEntrySnapshotFactory.create_batch(5, panel=gps)
        gene_symbol = genes[2].gene["gene_symbol"]

        number_of_genes = gps.stats.get("number_of_genes")

        url = reverse_lazy(
            "panels:delete_entity",
            kwargs={
                "pk": gps.panel.pk,
                "entity_type": "gene",
                "entity_name": gene_symbol,
            },
        )
        res = self.client.get(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")

        new_gps = GenePanel.objects.get(pk=gps.panel.pk).active_panel
        assert new_gps.has_gene(gene_symbol) is False
        assert number_of_genes - 1 == new_gps.stats.get(
            "number_of_genes"
        )  # 4 is due to create_batch
        assert res.json().get("status") == 200
        assert res.json().get("content").get("inner-fragments")

    def test_active_panel(self):
        """
        Make sure GenePanel.active_panel returns correct panel
        """

        gps = GenePanelSnapshotFactory(panel__status=GenePanel.STATUS.public)
        gps2 = GenePanelSnapshotFactory(panel__status=GenePanel.STATUS.public)
        gps.panel.active_panel.increment_version()
        gps.panel.active_panel.increment_version()
        gps.panel.active_panel.increment_version()
        gps.panel.active_panel.increment_version()
        gps.panel.active_panel.increment_version()
        gps = gps.panel.active_panel

        assert gps.minor_version == 5

        gp = GenePanel.objects.get(pk=gps.panel.pk)
        assert gp.active_panel == gps

        gps2.panel.active_panel.increment_version()
        del gps2.panel.active_panel
        gps2.panel.active_panel.increment_version()

        del gps2.panel.active_panel
        gps2 = gps2.panel.active_panel

        assert gps2.minor_version == 2
        gp2 = GenePanel.objects.get(pk=gps2.panel.pk)
        assert gp2.active_panel == gps2

    def prepare_compare(self):
        gene = GeneFactory()

        gps = GenePanelSnapshotFactory(panel__status=GenePanel.STATUS.internal)
        GenePanelEntrySnapshotFactory.create_batch(2, panel=gps)  # random genes
        GenePanelEntrySnapshotFactory.create(gene_core=gene, panel=gps)

        gps2 = GenePanelSnapshotFactory(panel__status=GenePanel.STATUS.public)
        GenePanelEntrySnapshotFactory.create_batch(2, panel=gps2)  # random genes
        GenePanelEntrySnapshotFactory.create(gene_core=gene, panel=gps2)

        STRFactory(panel=gps, position_37=None)

        return gene, gps, gps2

    def test_compare_panels(self):
        gene, gps, gps2 = self.prepare_compare()

        data = {"panel_1": gps.pk, "panel_2": gps2.pk}

        url = reverse_lazy("panels:compare_panels_form")
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)

        url = reverse_lazy("panels:compare", args=(gps.panel.pk, gps2.panel.pk))
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)

        url = reverse_lazy("panels:compare", args=(gps.panel.pk, gps2.panel.pk))
        res = self.client.post(url, data)
        self.assertEqual(res.status_code, 302)

        url = reverse_lazy(
            "panels:compare_genes", args=(gps.panel.pk, gps2.panel.pk, gene.gene_symbol)
        )
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)

        url = reverse_lazy(
            "panels:compare_genes", args=(gps.panel.pk, gps2.panel.pk, gene.gene_symbol)
        )
        res = self.client.post(url, data)
        self.assertEqual(res.status_code, 302)

    def test_copy_reviews(self):
        gene, gps, gps2 = self.prepare_compare()

        res = self.client.get(
            reverse_lazy("panels:copy_reviews", args=(gps.panel.pk, gps2.panel.pk))
        )
        self.assertEqual(res.status_code, 200)
        data = {"panel_1": gps.pk, "panel_2": gps2.pk}
        res = self.client.post(
            reverse_lazy("panels:copy_reviews", args=(gps.panel.pk, gps2.panel.pk)),
            data,
        )
        self.assertEqual(res.status_code, 302)

    def test_compare_genes(self):
        gene, gps, gps2 = self.prepare_compare()
        res = self.client.get(
            reverse_lazy(
                "panels:compare_genes",
                args=(gps.panel.pk, gps2.panel.pk, gene.gene_symbol),
            )
        )
        self.assertEqual(res.status_code, 200)

    def test_promote_panel(self):
        gpes = GenePanelEntrySnapshotFactory()

        data = {"version_comment": fake.sentence()}
        url = reverse_lazy("panels:promote", args=(gpes.panel.panel.pk,))
        res = self.client.post(url, data)
        self.assertEqual(res.status_code, 302)

    def test_import_view(self):
        r = self.client.get(reverse_lazy("panels:admin"))
        self.assertEqual(r.status_code, 200)

    def test_import_panel(self):
        GeneFactory(gene_symbol="ABCC5-AS1")
        GeneFactory(gene_symbol="A1CF")
        GeneFactory(gene_symbol="STR_1")
        GeneFactory(gene_symbol="STR_2")

        file_path = os.path.join(os.path.dirname(__file__), "import_panel_data.tsv")
        test_panel_file = os.path.abspath(file_path)

        with open(test_panel_file) as f:
            url = reverse_lazy("panels:upload_panels")
            res = self.client.post(url, {"panel_list": f})

        gp = GenePanel.objects.get(name="Panel One")
        active_panel = gp.active_panel
        entries = active_panel.get_all_genes
        self.assertEqual(entries.count(), 2)

    def test_import_regions(self):
        GeneFactory(gene_symbol="ABCC5-AS1")
        GeneFactory(gene_symbol="A1CF")
        GeneFactory(gene_symbol="STR_1")
        GeneFactory(gene_symbol="STR_2")

        file_path = os.path.join(os.path.dirname(__file__), "import_panel_data.tsv")
        test_panel_file = os.path.abspath(file_path)

        with open(test_panel_file) as f:
            url = reverse_lazy("panels:upload_panels")
            res = self.client.post(url, {"panel_list": f})

        gp = GenePanel.objects.get(name="Panel One")
        active_panel = gp.active_panel
        self.assertEqual(active_panel.get_all_regions.count(), 1)

    def test_import_strs(self):
        GeneFactory(gene_symbol="ABCC5-AS1")
        GeneFactory(gene_symbol="A1CF")
        gene = GeneFactory(gene_symbol="STR_1")
        GeneFactory(gene_symbol="STR_2")
        GeneFactory(gene_symbol="STR_3")

        file_path = os.path.join(os.path.dirname(__file__), "import_panel_data.tsv")
        test_panel_file = os.path.abspath(file_path)

        with open(test_panel_file) as f:
            url = reverse_lazy("panels:upload_panels")
            res = self.client.post(url, {"panel_list": f})

        self.assertEqual(GenePanel.objects.count(), 2)
        gp = GenePanel.objects.get(name="TestPanel")
        active_panel = gp.active_panel
        self.assertEqual(active_panel.get_all_strs.count(), 3)
        self.assertEqual(active_panel.get_str("STR_1").gene_core, gene)
        self.assertEqual(active_panel.get_str("STR_2").gene_core, None)
        self.assertEqual(active_panel.get_str("STR_3").gene_core, None)

    def test_import_panel_sources(self):
        gene = GeneFactory(gene_symbol="ABCC5-AS1")
        A1CF = GeneFactory(gene_symbol="A1CF")
        GeneFactory(gene_symbol="STR_1")
        GeneFactory(gene_symbol="STR_2")

        gps = GenePanelSnapshotFactory()
        gps.panel.name = "Panel One"
        gps.level4title.name = gps.panel.name
        gps.level4title.save()
        gps.panel.save()
        evidence = EvidenceFactory.create(name="Expert Review Amber")
        GenePanelEntrySnapshotFactory.create(
            gene_core=gene, panel=gps, evaluation=(None,), evidence=(evidence,)
        )
        self.assertEqual(
            gps.get_gene(gene.gene_symbol).evidence.first().name, "Expert Review Amber"
        )

        file_path = os.path.join(os.path.dirname(__file__), "import_panel_data.tsv")
        test_panel_file = os.path.abspath(file_path)

        with open(test_panel_file) as f:
            url = reverse_lazy("panels:upload_panels")
            self.client.post(url, {"panel_list": f})

        ap = GenePanel.objects.get(name="Panel One").active_panel
        self.assertEqual(
            ap.get_gene(gene.gene_symbol).evidence.first().name, "Expert Review Green"
        )
        self.assertEqual(ap.get_gene(gene.gene_symbol).evidence.count(), 1)
        self.assertEqual(sorted(ap.get_gene("A1CF").phenotypes), sorted(["57h", "wef"]))

    def test_import_incorrect_position(self):
        GeneFactory(gene_symbol="STR_1")

        file_path = os.path.join(
            os.path.dirname(__file__), "import_panel_data_error.tsv"
        )
        test_panel_file = os.path.abspath(file_path)

        with open(test_panel_file) as f:
            url = reverse_lazy("panels:upload_panels")
            res = self.client.post(url, {"panel_list": f})
            messages = [str(m) for m in res.wsgi_request._messages]
            expected_messages = [
                "Line: 3, 4, 5 is not properly formatted, please check it and try again."
            ]
            self.assertEqual(expected_messages, messages)

        self.assertEqual(GenePanel.objects.count(), 0)

    def test_import_wrong_panel(self):
        file_path = os.path.join(os.path.dirname(__file__), "import_panel_data.tsv")
        test_panel_file = os.path.abspath(file_path)

        with open(test_panel_file) as f:
            url = reverse_lazy("panels:upload_panels")
            res = self.client.post(url, {"panel_list": f})
            for message in res.wsgi_request._messages:
                assert "ABCC5-AS1" in message.message

        assert GenePanelEntrySnapshot.objects.count() == 0

    def test_download_panel(self):
        gene, gps, gps2 = self.prepare_compare()
        grey_gene = "gene2"
        gene2 = GeneFactory(gene_symbol=grey_gene)
        gpes = GenePanelEntrySnapshotFactory.create(gene_core=gene2, panel=gps)
        gpes.saved_gel_status = 0

        res = self.client.get(
            reverse_lazy("panels:download_panel_tsv", args=(gps.panel.pk, "01234"))
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.content.find(grey_gene.encode()), -1)

    def test_download_old_panel(self):
        gene, gps, gps2 = self.prepare_compare()
        gps.increment_version()

        data = {"panel_version": "0.1"}

        res = self.client.post(
            reverse_lazy("panels:download_old_panel_tsv", args=(gps.panel.pk,)), data
        )
        self.assertEqual(res.status_code, 200)

    def test_download_old_panel_wrong_version(self):
        gene, gps, gps2 = self.prepare_compare()
        data = {"panel_version": "1.125"}

        res = self.client.post(
            reverse_lazy("panels:download_old_panel_tsv", args=(gps.panel.pk,)), data
        )
        self.assertEqual(res.status_code, 302)

    def test_download_all_panels(self):
        gps = GenePanelSnapshotFactory()
        GenePanelEntrySnapshotFactory.create_batch(2, panel=gps)

        res = self.client.get(reverse_lazy("panels:download_panels"))
        self.assertEqual(res.status_code, 200)

    def test_email_panel_promoted(self):
        gpes = GenePanelEntrySnapshotFactory()
        email_panel_promoted(gpes.panel.panel.pk)
        self.assertEqual(len(mail.outbox), 4)

    def test_old_pk_redirect(self):
        gpes = GenePanelEntrySnapshotFactory()
        gpes.panel.panel.old_pk = fake.password(
            length=24, special_chars=False, upper_case=False
        )
        gpes.panel.panel.save()

        res = self.client.get(
            reverse_lazy(
                "panels:old_code_url_redirect", args=(gpes.panel.panel.old_pk, "")
            )
        )
        self.assertEqual(res.status_code, 301)
        self.assertEqual(
            res.url, reverse_lazy("panels:detail", args=(gpes.panel.panel.pk,))
        )

        res = self.client.get(
            reverse_lazy(
                "panels:old_code_url_redirect",
                args=(gpes.panel.panel.old_pk, "gene/" + gpes.gene.get("gene_symbol")),
            )
        )
        self.assertEqual(res.status_code, 301)
        self.assertEqual(
            res.url + "/",
            reverse_lazy(
                "panels:evaluation",
                args=(gpes.panel.panel.id, "gene", gpes.gene.get("gene_symbol")),
            ),
        )

    def test_evaluation_stays(self):
        gps = GenePanelSnapshotFactory()
        gpes = GenePanelEntrySnapshotFactory(panel=gps)
        evaluations = gpes.evaluation.all()
        gpes2 = GenePanelEntrySnapshotFactory(panel=gps)
        evaluations2 = sorted(gpes2.evaluation.all().values_list("pk", flat=True))

        gps = gps.increment_version()
        gps.update_gene(
            self.gel_user, gpes.gene_core.gene_symbol, {"phenotypes": ["abra"]}
        )
        del gps.panel.active_panel
        current_ev2 = sorted(
            gps.panel.active_panel.get_gene(gpes2.gene_core.gene_symbol)
            .evaluation.all()
            .values_list("pk", flat=True)
        )

        self.assertEqual(evaluations2, current_ev2)

    def test_evaluation_single_panel(self):
        gps = GenePanelSnapshotFactory()
        gpes = GenePanelEntrySnapshotFactory(panel=gps)
        gps.panel.active_panel.increment_version()
        gps.panel.active_panel.increment_version()
        gps = gps.panel.active_panel

        gene_symbol = gpes.gene_core.gene_symbol

        # check we copy evaluation rather than assign it
        current_count = (
            gps.panel.active_panel.get_all_genes[0]
            .evaluation.first()
            .genepanelentrysnapshot_set.count()
        )
        self.assertEqual(current_count, 1)

        # check if deleting gene preserves it in the previous versions
        gp = gps.panel
        gps.delete_gene(gene_symbol)
        v1 = HistoricalSnapshot.objects.filter(
            panel=gps.panel, major_version=0, minor_version=1
        ).first()
        assert gene_symbol in [g["entity_name"] for g in v1.data["genes"]]

    def test_panel_types(self):
        panel_type = PanelTypeFactory()
        gpes = GenePanelEntrySnapshotFactory()

        panel_data = self.panel_data
        panel_data["types"] = [panel_type.pk]
        res = self.client.post(reverse_lazy("panels:create"), panel_data)
        self.assertEqual(res.status_code, 302)

        gp = GenePanel.objects.get(name=self.panel_data["level4"])
        self.assertEqual(gp.types.first(), panel_type)
        r = self.client.get(reverse_lazy("panels:detail", args=(gp.pk,)))
        self.assertIn(panel_type.name.encode(), r.content)

    def test_panel_type_displayed(self):
        panel_type = PanelTypeFactory()
        gpes = GenePanelEntrySnapshotFactory()

        panel_data = self.panel_data
        panel_data["types"] = [panel_type.pk]
        res = self.client.post(reverse_lazy("panels:create"), panel_data)
        self.assertEqual(res.status_code, 302)

        res = self.client.get(reverse_lazy("panels:index"))
        self.assertIn(panel_type.name.encode(), res.content)
