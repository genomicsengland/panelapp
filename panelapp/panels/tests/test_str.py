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
from random import randint
from django.core import mail
from django.test import Client
from django.urls import reverse_lazy
from faker import Factory
from accounts.tests.setup import LoginGELUser
from panels.models import GenePanel
from panels.models import GenePanelEntrySnapshot
from panels.models import Evaluation
from panels.models import Evidence
from panels.models import GenePanelSnapshot
from panels.models import HistoricalSnapshot
from panels.tasks import email_panel_promoted
from panels.tests.factories import GeneFactory
from panels.tests.factories import GenePanelSnapshotFactory
from panels.tests.factories import GenePanelEntrySnapshotFactory
from panels.tests.factories import STRFactory
from panels.tests.factories import TagFactory
from panels.tests.factories import CommentFactory


fake = Factory.create()


class STRTest(LoginGELUser):
    def test_str_data_copied(self):
        gpes = GenePanelEntrySnapshotFactory()
        active_panel = gpes.panel
        str_item = active_panel.add_str(
            self.gel_user,
            "ABC",
            {
                "gene": gpes.gene_core,
                "chromosome": "1",
                "position_37": (12345, 12346),
                "position_38": (12345, 12346),
                "repeated_sequence": "ATAT",
                "normal_repeats": "2",
                "pathogenic_repeats": "5",
                "panel": active_panel,
                "moi": "X-LINKED: hemizygous mutation in males, biallelic mutations in females",
                "penetrance": "Incomplete",
                "publications": None,
                "phenotypes": None,
                "sources": [],
            },
        )

        active_panel = active_panel.panel.active_panel

        assert active_panel.has_str(str_item.name)
        active_panel.increment_version()
        active_panel = active_panel.panel.active_panel
        assert active_panel.panel.active_panel.has_str(str_item.name)

    def test_add_str_to_panel(self):
        gene = GeneFactory()
        gps = GenePanelSnapshotFactory()

        number_of_strs = gps.stats.get("number_of_strs", 0)

        url = reverse_lazy(
            "panels:add_entity", kwargs={"pk": gps.panel.pk, "entity_type": "str"}
        )
        gene_data = {
            "name": "SomeSTR",
            "chromosome": "1",
            "position_37_0": "",
            "position_37_1": "",
            "position_38_0": "12345",
            "position_38_1": "123456",
            "repeated_sequence": "ATAT",
            "normal_repeats": "2",
            "pathogenic_repeats": "5",
            "gene": gene.pk,
            "source": Evidence.ALL_SOURCES[randint(0, 9)],
            "tags": [TagFactory().pk],
            "publications": "{};{};{}".format(*fake.sentences(nb=3)),
            "phenotypes": "{};{};{}".format(*fake.sentences(nb=3)),
            "rating": Evaluation.RATINGS.AMBER,
            "comments": fake.sentence(),
            "moi": [x for x in Evaluation.MODES_OF_INHERITANCE][randint(1, 12)][0],
            "penetrance": GenePanelEntrySnapshot.PENETRANCE.Incomplete,
            "current_diagnostic": "True",
        }
        res = self.client.post(url, gene_data)

        new_current_number = gps.panel.active_panel.stats.get("number_of_strs")

        assert gps.panel.active_panel.version != gps.version

        assert res.status_code == 302
        assert number_of_strs + 1 == new_current_number

        # make sure tags are added
        new_str = GenePanel.objects.get(pk=gps.panel.pk).active_panel.get_str(
            gene_data["name"]
        )
        assert sorted(list(new_str.tags.all().values_list("pk", flat=True))) == sorted(
            gene_data["tags"]
        )

    def test_add_str_to_panel_no_gene_data(self):
        """STRs can exist without genes"""

        gps = GenePanelSnapshotFactory()

        number_of_strs = gps.stats.get("number_of_strs", 0)

        url = reverse_lazy(
            "panels:add_entity", kwargs={"pk": gps.panel.pk, "entity_type": "str"}
        )
        gene_data = {
            "name": "SomeSTR",
            "chromosome": "1",
            "position_37_0": "12345",
            "position_37_1": "12346",
            "position_38_0": "12345",
            "position_38_1": "123456",
            "repeated_sequence": "ATAT",
            "normal_repeats": "2",
            "pathogenic_repeats": "5",
            "source": Evidence.ALL_SOURCES[randint(0, 9)],
            "tags": [TagFactory().pk],
            "publications": "{};{};{}".format(*fake.sentences(nb=3)),
            "phenotypes": "{};{};{}".format(*fake.sentences(nb=3)),
            "rating": Evaluation.RATINGS.AMBER,
            "comments": fake.sentence(),
            "moi": [x for x in Evaluation.MODES_OF_INHERITANCE][randint(1, 12)][0],
            "penetrance": GenePanelEntrySnapshot.PENETRANCE.Incomplete,
            "current_diagnostic": "True",
        }
        res = self.client.post(url, gene_data)

        new_current_number = gps.panel.active_panel.stats.get("number_of_strs")

        assert gps.panel.active_panel.version != gps.version

        assert res.status_code == 302
        assert number_of_strs + 1 == new_current_number

    def test_gel_curator_str_red(self):
        """When gene is added by a GeL currator it should be marked as red"""

        gene = GeneFactory()
        gps = GenePanelSnapshotFactory()
        url = reverse_lazy(
            "panels:add_entity", kwargs={"pk": gps.panel.pk, "entity_type": "str"}
        )
        str_data = {
            "name": "SomeSTR",
            "chromosome": "1",
            "position_37_0": "12345",
            "position_37_1": "12346",
            "position_38_0": "12345",
            "position_38_1": "123456",
            "repeated_sequence": "ATAT",
            "normal_repeats": "2",
            "pathogenic_repeats": "5",
            "gene": gene.pk,
            "source": Evidence.OTHER_SOURCES[0],
            "phenotypes": "{};{};{}".format(*fake.sentences(nb=3)),
            "rating": Evaluation.RATINGS.AMBER,
            "moi": [x for x in Evaluation.MODES_OF_INHERITANCE][randint(1, 12)][0],
            "mode_of_pathogenicity": [x for x in Evaluation.MODES_OF_PATHOGENICITY][
                randint(1, 2)
            ][0],
            "penetrance": GenePanelEntrySnapshot.PENETRANCE.Incomplete,
        }
        self.client.post(url, str_data)
        panel = gps.panel.active_panel

        assert panel.get_str("SomeSTR").saved_gel_status == 1

    def test_str_evaluation(self):
        str_item = STRFactory()
        url = reverse_lazy(
            "panels:evaluation",
            kwargs={
                "pk": str_item.panel.panel.pk,
                "entity_type": "str",
                "entity_name": str_item.name,
            },
        )
        res = self.client.get(url)
        assert res.status_code == 200

    def test_edit_str_in_panel(self):
        str_item = STRFactory()
        url = reverse_lazy(
            "panels:edit_entity",
            kwargs={
                "pk": str_item.panel.panel.pk,
                "entity_type": "str",
                "entity_name": str_item.name,
            },
        )

        number_of_strs = str_item.panel.stats.get("number_of_strs")

        # make sure new data has at least 1 of the same items
        source = str_item.evidence.last().name

        publication = str_item.publications[0]
        phenotype = str_item.publications[1]

        new_evidence = Evidence.ALL_SOURCES[randint(0, 9)]
        original_evidences = set([ev.name for ev in str_item.evidence.all()])
        original_evidences.add(new_evidence)

        str_data = {
            "name": str_item.name,
            "chromosome": "1",
            "position_37_0": "12345",
            "position_37_1": "12346",
            "position_38_0": "12345",
            "position_38_1": "123456",
            "repeated_sequence": "ATAT",
            "normal_repeats": "2",
            "pathogenic_repeats": "5",
            "gene": str_item.gene_core.pk,
            "gene_name": "Gene name",
            "source": set([source, new_evidence]),
            "tags": [TagFactory().pk] + [tag.pk for tag in str_item.tags.all()],
            "publications": ";".join([publication, fake.sentence()]),
            "phenotypes": ";".join([phenotype, fake.sentence(), fake.sentence()]),
            "moi": [x for x in Evaluation.MODES_OF_INHERITANCE][randint(1, 12)][0],
            "penetrance": GenePanelEntrySnapshot.PENETRANCE.Incomplete,
        }
        res = self.client.post(url, str_data)
        assert res.status_code == 302
        new_str = GenePanel.objects.get(
            pk=str_item.panel.panel.pk
        ).active_panel.get_str(str_item.name)
        assert str_item.panel.panel.active_panel.version != str_item.panel.version
        new_current_number = new_str.panel.panel.active_panel.stats.get(
            "number_of_strs"
        )
        assert number_of_strs == new_current_number
        self.assertEqual(int(str_data["position_37_1"]), new_str.position_37.upper)

    def test_edit_repeated_sequence(self):
        str_item = STRFactory()
        url = reverse_lazy(
            "panels:edit_entity",
            kwargs={
                "pk": str_item.panel.panel.pk,
                "entity_type": "str",
                "entity_name": str_item.name,
            },
        )

        number_of_strs = str_item.panel.stats.get("number_of_strs")

        # make sure new data has at least 1 of the same items
        source = str_item.evidence.last().name

        publication = str_item.publications[0]
        phenotype = str_item.publications[1]

        new_evidence = Evidence.ALL_SOURCES[randint(0, 9)]
        original_evidences = set([ev.name for ev in str_item.evidence.all()])
        original_evidences.add(new_evidence)

        str_data = {
            "name": str_item.name,
            "chromosome": "1",
            "position_37_0": "12345",
            "position_37_1": "12346",
            "position_38_0": "12345",
            "position_38_1": "123456",
            "repeated_sequence": "ATATAT",
            "normal_repeats": "2",
            "pathogenic_repeats": "5",
            "gene": str_item.gene_core.pk,
            "gene_name": "Gene name",
            "source": set([source, new_evidence]),
            "tags": [TagFactory().pk] + [tag.pk for tag in str_item.tags.all()],
            "publications": ";".join([publication, fake.sentence()]),
            "phenotypes": ";".join([phenotype, fake.sentence(), fake.sentence()]),
            "moi": [x for x in Evaluation.MODES_OF_INHERITANCE][randint(1, 12)][0],
            "penetrance": GenePanelEntrySnapshot.PENETRANCE.Incomplete,
        }
        res = self.client.post(url, str_data)
        assert res.status_code == 302
        new_str = GenePanel.objects.get(
            pk=str_item.panel.panel.pk
        ).active_panel.get_str(str_item.name)
        assert new_str.repeated_sequence == "ATATAT"

    def test_edit_incorrect_repeated_sequence(self):
        str_item = STRFactory()
        url = reverse_lazy(
            "panels:edit_entity",
            kwargs={
                "pk": str_item.panel.panel.pk,
                "entity_type": "str",
                "entity_name": str_item.name,
            },
        )

        number_of_strs = str_item.panel.stats.get("number_of_strs")

        # make sure new data has at least 1 of the same items
        source = str_item.evidence.last().name

        publication = str_item.publications[0]
        phenotype = str_item.publications[1]

        new_evidence = Evidence.ALL_SOURCES[randint(0, 9)]
        original_evidences = set([ev.name for ev in str_item.evidence.all()])
        original_evidences.add(new_evidence)

        str_data = {
            "name": str_item.name,
            "chromosome": "1",
            "position_37_0": "12345",
            "position_37_1": "12346",
            "position_38_0": "12345",
            "position_38_1": "123456",
            "repeated_sequence": "ATATBC",
            "normal_repeats": "2",
            "pathogenic_repeats": "5",
            "gene": str_item.gene_core.pk,
            "gene_name": "Gene name",
            "source": set([source, new_evidence]),
            "tags": [TagFactory().pk] + [tag.pk for tag in str_item.tags.all()],
            "publications": ";".join([publication, fake.sentence()]),
            "phenotypes": ";".join([phenotype, fake.sentence(), fake.sentence()]),
            "moi": [x for x in Evaluation.MODES_OF_INHERITANCE][randint(1, 12)][0],
            "penetrance": GenePanelEntrySnapshot.PENETRANCE.Incomplete,
        }
        res = self.client.post(url, str_data)
        assert res.status_code == 200
        assert (
            res.content.find(b"Repeated sequence contains incorrect nucleotides") != -1
        )

    def test_remove_gene_from_str(self):
        """We need ability to remove genes from STRs"""

        str_item = STRFactory()
        url = reverse_lazy(
            "panels:edit_entity",
            kwargs={
                "pk": str_item.panel.panel.pk,
                "entity_type": "str",
                "entity_name": str_item.name,
            },
        )

        number_of_strs = str_item.panel.stats.get("number_of_strs", 0)

        # make sure new data has at least 1 of the same items
        source = str_item.evidence.last().name

        publication = str_item.publications[0]
        phenotype = str_item.publications[1]

        new_evidence = Evidence.ALL_SOURCES[randint(0, 9)]
        original_evidences = set([ev.name for ev in str_item.evidence.all()])
        original_evidences.add(new_evidence)

        str_data = {
            "name": str_item.name,
            "chromosome": "1",
            "position_37_0": "12345",
            "position_37_1": "12346",
            "position_38_0": "12345",
            "position_38_1": "123456",
            "repeated_sequence": "ATAT",
            "normal_repeats": "2",
            "pathogenic_repeats": "5",
            "gene_name": "Gene name",
            "source": set([source, new_evidence]),
            "tags": [TagFactory().pk] + [tag.pk for tag in str_item.tags.all()],
            "publications": ";".join([publication, fake.sentence()]),
            "phenotypes": ";".join([phenotype, fake.sentence(), fake.sentence()]),
            "moi": [x for x in Evaluation.MODES_OF_INHERITANCE][randint(1, 12)][0],
            "penetrance": GenePanelEntrySnapshot.PENETRANCE.Incomplete,
        }
        res = self.client.post(url, str_data)
        assert res.status_code == 302
        new_str = GenePanel.objects.get(
            pk=str_item.panel.panel.pk
        ).active_panel.get_str(str_item.name)
        assert not new_str.gene_core
        assert not new_str.gene
        assert str_item.panel.panel.active_panel.version != str_item.panel.version
        new_current_number = new_str.panel.panel.active_panel.stats.get(
            "number_of_strs"
        )
        assert number_of_strs == new_current_number

    def test_remove_sources(self):
        """Remove sources via edit gene detail section"""

        str_item = STRFactory(penetrance=GenePanelEntrySnapshot.PENETRANCE.Incomplete)
        url = reverse_lazy(
            "panels:edit_entity",
            kwargs={
                "pk": str_item.panel.panel.pk,
                "entity_type": "str",
                "entity_name": str_item.name,
            },
        )

        str_data = {
            "name": str_item.name,
            "chromosome": "1",
            "position_37_0": "12345",
            "position_37_1": "12346",
            "position_38_0": "12345",
            "position_38_1": "123456",
            "repeated_sequence": "ATAT",
            "normal_repeats": "2",
            "pathogenic_repeats": "5",
            "gene": str_item.gene_core.pk,
            "gene_name": "Gene name",
            "source": set([ev.name for ev in str_item.evidence.all()[1:]]),
            "tags": [tag.pk for tag in str_item.tags.all()],
            "publications": ";".join(
                [publication for publication in str_item.publications]
            ),
            "phenotypes": ";".join([phenotype for phenotype in str_item.phenotypes]),
            "moi": str_item.moi,
            "penetrance": GenePanelEntrySnapshot.PENETRANCE.Complete,
        }
        res = self.client.post(url, str_data)
        assert res.status_code == 302
        new_str = GenePanel.objects.get(
            pk=str_item.panel.panel.pk
        ).active_panel.get_str(str_item.name)
        assert new_str.penetrance != str_item.penetrance

    def test_add_tag_via_edit_details(self):
        """Set tags via edit gene detail section"""

        str_item = STRFactory(penetrance=GenePanelEntrySnapshot.PENETRANCE.Incomplete)
        url = reverse_lazy(
            "panels:edit_entity",
            kwargs={
                "pk": str_item.panel.panel.pk,
                "entity_type": "str",
                "entity_name": str_item.name,
            },
        )

        tag = TagFactory(name="some tag")

        str_data = {
            "name": str_item.name,
            "chromosome": "1",
            "position_37_0": "12345",
            "position_37_1": "12346",
            "position_38_0": "12345",
            "position_38_1": "123456",
            "repeated_sequence": "ATAT",
            "normal_repeats": "2",
            "pathogenic_repeats": "5",
            "gene": str_item.gene_core.pk,
            "gene_name": "Gene name",
            "source": set([ev.name for ev in str_item.evidence.all()]),
            "tags": [tag.pk for tag in str_item.tags.all()] + [tag.pk],
            "publications": ";".join(
                [publication for publication in str_item.publications]
            ),
            "phenotypes": ";".join([phenotype for phenotype in str_item.phenotypes]),
            "moi": str_item.moi,
            "penetrance": GenePanelEntrySnapshot.PENETRANCE.Complete,
        }
        res = self.client.post(url, str_data)
        assert res.status_code == 302
        new_str = GenePanel.objects.get(
            pk=str_item.panel.panel.pk
        ).active_panel.get_str(str_item.name)
        old_version = HistoricalSnapshot.objects.filter(panel=str_item.panel.panel).first()

        assert sorted(list(new_str.tags.values_list("pk"))) != sorted(
            list(g["tags"] for g in old_version.data["strs"])
        )

    def test_remove_tag_via_edit_details(self):
        """Remove tags via edit gene detail section"""

        str_item = STRFactory(penetrance=GenePanelEntrySnapshot.PENETRANCE.Incomplete)

        tag = TagFactory(name="some tag")
        str_item.tags.add(tag)

        url = reverse_lazy(
            "panels:edit_entity",
            kwargs={
                "pk": str_item.panel.panel.pk,
                "entity_type": "str",
                "entity_name": str_item.name,
            },
        )

        str_data = {
            "name": str_item.name,
            "chromosome": "1",
            "position_37_0": "12345",
            "position_37_1": "12346",
            "position_38_0": "12345",
            "position_38_1": "123456",
            "repeated_sequence": "ATAT",
            "normal_repeats": "2",
            "pathogenic_repeats": "5",
            "gene": str_item.gene_core.pk,
            "gene_name": "Gene name",
            "source": set([ev.name for ev in str_item.evidence.all()]),
            "tags": [],
            "publications": ";".join(
                [publication for publication in str_item.publications]
            ),
            "phenotypes": ";".join([phenotype for phenotype in str_item.phenotypes]),
            "moi": str_item.moi,
            "penetrance": GenePanelEntrySnapshot.PENETRANCE.Complete,
        }
        res = self.client.post(url, str_data)
        assert res.status_code == 302
        new_str = GenePanel.objects.get(
            pk=str_item.panel.panel.pk
        ).active_panel.get_str(str_item.name)
        assert list(new_str.tags.all()) == []

    def test_change_penetrance(self):
        """Test if a curator can change Gene penetrance"""

        str_item = STRFactory(penetrance=GenePanelEntrySnapshot.PENETRANCE.Incomplete)
        url = reverse_lazy(
            "panels:edit_entity",
            kwargs={
                "pk": str_item.panel.panel.pk,
                "entity_type": "str",
                "entity_name": str_item.name,
            },
        )

        str_data = {
            "name": str_item.name,
            "chromosome": "1",
            "position_37_0": "12345",
            "position_37_1": "12346",
            "position_38_0": "12345",
            "position_38_1": "123456",
            "repeated_sequence": "ATAT",
            "normal_repeats": "2",
            "pathogenic_repeats": "5",
            "gene": str_item.gene_core.pk,
            "gene_name": "Gene name",
            "source": set([ev.name for ev in str_item.evidence.all()]),
            "tags": [tag.pk for tag in str_item.tags.all()],
            "publications": ";".join(
                [publication for publication in str_item.publications]
            ),
            "phenotypes": ";".join([phenotype for phenotype in str_item.phenotypes]),
            "moi": str_item.moi,
            "penetrance": GenePanelEntrySnapshot.PENETRANCE.Complete,
        }
        res = self.client.post(url, str_data)
        assert res.status_code == 302
        new_str = GenePanel.objects.get(
            pk=str_item.panel.panel.pk
        ).active_panel.get_str(str_item.name)
        assert new_str.penetrance != str_item.penetrance

    def test_add_publication(self):
        """Add a publication to a gene panel entry"""

        str_item = STRFactory(penetrance=GenePanelEntrySnapshot.PENETRANCE.Incomplete)
        str_item.publications = []
        str_item.save()

        url = reverse_lazy(
            "panels:edit_entity",
            kwargs={
                "pk": str_item.panel.panel.pk,
                "entity_type": "str",
                "entity_name": str_item.name,
            },
        )

        str_data = {
            "name": str_item.name,
            "chromosome": "1",
            "position_37_0": "12345",
            "position_37_1": "12346",
            "position_38_0": "12345",
            "position_38_1": "123456",
            "repeated_sequence": "ATAT",
            "normal_repeats": "2",
            "pathogenic_repeats": "5",
            "gene": str_item.gene_core.pk,
            "gene_name": "Gene name",
            "source": set([ev.name for ev in str_item.evidence.all()]),
            "tags": [tag.pk for tag in str_item.tags.all()],
            "publications": ";".join([fake.sentence(), fake.sentence()]),
            "phenotypes": ";".join([phenotype for phenotype in str_item.phenotypes]),
            "moi": str_item.moi,
            "penetrance": GenePanelEntrySnapshot.PENETRANCE.Complete,
        }
        res = self.client.post(url, str_data)
        assert res.status_code == 302
        new_str = GenePanel.objects.get(
            pk=str_item.panel.panel.pk
        ).active_panel.get_str(str_item.name)
        assert new_str.publications != str_item.publications

    def test_remove_publication(self):
        """Remove a publication to a gene panel entry"""

        str_item = STRFactory(penetrance=GenePanelEntrySnapshot.PENETRANCE.Incomplete)
        str_item.publications = [fake.sentence(), fake.sentence()]
        str_item.save()

        url = reverse_lazy(
            "panels:edit_entity",
            kwargs={
                "pk": str_item.panel.panel.pk,
                "entity_type": "str",
                "entity_name": str_item.name,
            },
        )

        str_data = {
            "name": str_item.name,
            "chromosome": "1",
            "position_37_0": "12345",
            "position_37_1": "12346",
            "position_38_0": "12345",
            "position_38_1": "123456",
            "repeated_sequence": "ATAT",
            "normal_repeats": "2",
            "pathogenic_repeats": "5",
            "gene": str_item.gene_core.pk,
            "gene_name": "Gene name",
            "source": set([ev.name for ev in str_item.evidence.all()]),
            "tags": [tag.pk for tag in str_item.tags.all()],
            "publications": ";".join(str_item.publications[:1]),
            "phenotypes": ";".join([phenotype for phenotype in str_item.phenotypes]),
            "moi": str_item.moi,
            "penetrance": GenePanelEntrySnapshot.PENETRANCE.Complete,
        }
        res = self.client.post(url, str_data)
        assert res.status_code == 302
        new_str = GenePanel.objects.get(
            pk=str_item.panel.panel.pk
        ).active_panel.get_str(str_item.name)
        assert new_str.publications == str_item.publications[:1]

    def test_edit_str_name_unit(self):
        str_item = STRFactory()
        old_str_name = str_item.name

        ap = GenePanel.objects.get(pk=str_item.panel.panel.pk).active_panel

        assert ap.has_str(old_str_name) is True
        new_data = {"name": "NewSTR"}
        ap.update_str(self.verified_user, old_str_name, new_data)

        new_ap = GenePanel.objects.get(pk=str_item.panel.panel.pk).active_panel
        assert new_ap.has_str(old_str_name) is False
        assert new_ap.has_str("NewSTR") is True

    def test_update_str_preserves_comments_order(self):
        str_item = STRFactory()
        comments = list(CommentFactory.create_batch(4, user=self.verified_user))

        for ev in str_item.evaluation.all():
            ev.comments.add(comments.pop())

        max_comments_num = max([e.comments.count() for e in str_item.evaluation.all()])
        self.assertEqual(1, max_comments_num)

        old_str_name = str_item.name
        ap = GenePanel.objects.get(pk=str_item.panel.panel.pk).active_panel

        new_data = {"name": "NewSTR"}
        ap.update_str(self.verified_user, old_str_name, new_data)

        new_ap = GenePanel.objects.get(pk=str_item.panel.panel.pk).active_panel
        new_str = new_ap.get_str("NewSTR")

        max_comments_num_after_update = max(
            [e.comments.count() for e in new_str.evaluation.all()]
        )
        self.assertEqual(1, max_comments_num_after_update)

    def test_edit_str_name_ajax(self):
        str_item = STRFactory()
        url = reverse_lazy(
            "panels:edit_entity",
            kwargs={
                "pk": str_item.panel.panel.pk,
                "entity_type": "str",
                "entity_name": str_item.name,
            },
        )

        old_str_name = str_item.name

        # make sure new data has at least 1 of the same items
        source = str_item.evidence.last().name
        publication = str_item.publications[0]
        phenotype = str_item.publications[1]

        gene_data = {
            "name": "NewSTR",
            "chromosome": "1",
            "position_37_0": "12345",
            "position_37_1": "12346",
            "position_38_0": "12345",
            "position_38_1": "123456",
            "repeated_sequence": "ATAT",
            "normal_repeats": "2",
            "pathogenic_repeats": "5",
            "gene": str_item.gene_core.pk,
            "gene_name": "Other name",
            "source": set([source, Evidence.ALL_SOURCES[randint(0, 9)]]),
            "tags": [TagFactory().pk] + [tag.pk for tag in str_item.tags.all()],
            "publications": ";".join([publication, fake.sentence()]),
            "phenotypes": ";".join([phenotype, fake.sentence(), fake.sentence()]),
            "moi": [x for x in Evaluation.MODES_OF_INHERITANCE][randint(1, 12)][0],
            "penetrance": GenePanelEntrySnapshot.PENETRANCE.Incomplete,
        }
        res = self.client.post(url, gene_data)
        assert res.status_code == 302

        new_gps = GenePanel.objects.get(pk=str_item.panel.panel.pk).active_panel
        old_gps = HistoricalSnapshot.objects.get(panel=str_item.panel.panel)

        # check panel has no previous gene
        assert new_gps.has_str(old_str_name) is False

        # test previous panel contains old gene
        assert old_str_name in [g["entity_name"] for g in old_gps.data["strs"]]

    def test_download_panel_contains_strs(self):
        gpes = GenePanelEntrySnapshotFactory()
        gps = gpes.panel
        strs = STRFactory(repeated_sequence="ATATCGCGN", panel=gps)

        res = self.client.get(
            reverse_lazy("panels:download_panel_tsv", args=(gps.panel.pk, "01234"))
        )
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.content.find(strs.repeated_sequence.encode()) != 1)
