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
from random import randint
from django.urls import reverse_lazy
from faker import Factory
from accounts.tests.setup import LoginGELUser
from accounts.tests.setup import LoginReviewerUser
from panels.models import GenePanelEntrySnapshot
from panels.models import GenePanelSnapshot
from panels.models import Evidence
from panels.models import GenePanel
from panels.models import Evaluation
from panels.tests.factories import GeneFactory
from panels.tests.factories import GenePanelSnapshotFactory
from panels.tests.factories import GenePanelEntrySnapshotFactory
from panels.tests.factories import TagFactory
from panels.tests.factories import CommentFactory


fake = Factory.create()


class SuperPanelsTest(LoginGELUser):
    """GeL curator tests"""

    def test_have_child_entities(self):
        gene1 = GeneFactory()
        gene2 = GeneFactory()
        parent = GenePanelSnapshotFactory()

        gene1_data = {
            "gene": gene1.pk,
            "sources": [Evidence.OTHER_SOURCES[0]],
            "phenotypes": fake.sentences(nb=3),
            "rating": Evaluation.RATINGS.AMBER,
            "moi": [x for x in Evaluation.MODES_OF_INHERITANCE][randint(1, 12)][0],
            "mode_of_pathogenicity": [x for x in Evaluation.MODES_OF_PATHOGENICITY][
                randint(1, 2)
            ][0],
            "penetrance": GenePanelEntrySnapshot.PENETRANCE.Incomplete,
            "current_diagnostic": False,
        }

        gene2_data = {
            "gene": gene2.pk,
            "sources": [Evidence.OTHER_SOURCES[0]],
            "phenotypes": fake.sentences(nb=3),
            "rating": Evaluation.RATINGS.AMBER,
            "moi": [x for x in Evaluation.MODES_OF_INHERITANCE][randint(1, 12)][0],
            "mode_of_pathogenicity": [x for x in Evaluation.MODES_OF_PATHOGENICITY][
                randint(1, 2)
            ][0],
            "penetrance": GenePanelEntrySnapshot.PENETRANCE.Incomplete,
            "current_diagnostic": False,
        }

        child1 = GenePanelSnapshotFactory()
        child1.add_gene(self.gel_user, gene1.gene_symbol, gene1_data)
        child1.add_gene(self.gel_user, gene2.gene_symbol, gene2_data)

        child2 = GenePanelSnapshotFactory()
        child2.add_gene(self.gel_user, gene1.gene_symbol, gene1_data)

        parent.child_panels.set([child1, child2])
        parent._update_saved_stats()
        del parent.is_super_panel

        self.assertEqual(len(parent.get_all_entities_extra), 3)
        self.assertTrue(parent.is_super_panel)
        self.assertTrue(child1.is_child_panel)
        self.assertTrue(child2.is_child_panel)
        self.assertIn(child1.get_gene(gene1.gene_symbol), parent.get_all_entities_extra)
        self.assertIn(child1.get_gene(gene2.gene_symbol), parent.get_all_entities_extra)
        self.assertTrue(parent.genepanelentrysnapshot_set.count() == 0)

    def test_increment_version(self):
        gene1 = GeneFactory()
        gene2 = GeneFactory()
        parent = GenePanelSnapshotFactory(panel__status=GenePanel.STATUS.public)

        gene1_data = {
            "gene": gene1.pk,
            "sources": [Evidence.OTHER_SOURCES[0]],
            "phenotypes": fake.sentences(nb=3),
            "rating": Evaluation.RATINGS.AMBER,
            "moi": [x for x in Evaluation.MODES_OF_INHERITANCE][randint(1, 12)][0],
            "mode_of_pathogenicity": [x for x in Evaluation.MODES_OF_PATHOGENICITY][
                randint(1, 2)
            ][0],
            "penetrance": GenePanelEntrySnapshot.PENETRANCE.Incomplete,
            "current_diagnostic": False,
        }

        gene2_data = {
            "gene": gene2.pk,
            "sources": [Evidence.OTHER_SOURCES[0]],
            "phenotypes": fake.sentences(nb=3),
            "rating": Evaluation.RATINGS.AMBER,
            "moi": [x for x in Evaluation.MODES_OF_INHERITANCE][randint(1, 12)][0],
            "mode_of_pathogenicity": [x for x in Evaluation.MODES_OF_PATHOGENICITY][
                randint(1, 2)
            ][0],
            "penetrance": GenePanelEntrySnapshot.PENETRANCE.Incomplete,
            "current_diagnostic": False,
        }

        child1 = GenePanelSnapshotFactory(panel__status=GenePanel.STATUS.public)
        initial_child1_pk = child1.pk
        child1.add_gene(self.gel_user, gene1.gene_symbol, gene1_data)
        child1 = child1.panel.active_panel
        child1.add_gene(self.gel_user, gene2.gene_symbol, gene2_data)
        child1 = child1.panel.active_panel
        self.assertEqual(initial_child1_pk, child1.pk)

        child2 = GenePanelSnapshotFactory(panel__status=GenePanel.STATUS.public)
        initial_child2_pk = child2.pk
        child2.add_gene(self.gel_user, gene1.gene_symbol, gene1_data)
        del child2.panel.active_panel
        child2 = child2.panel.active_panel

        self.assertEqual(initial_child2_pk, child2.pk)

        parent.child_panels.set([child1, child2])
        parent._update_saved_stats()

        self.assertEqual(child1, child1.panel.active_panel)
        self.assertEqual(child2, child2.panel.active_panel)

        new_data = {
            "level2": fake.sentence(nb_words=6, variable_nb_words=True),
            "level3": fake.sentence(nb_words=6, variable_nb_words=True),
            "level4": fake.sentence(nb_words=6, variable_nb_words=True),
            "description": fake.text(max_nb_chars=300),
            "omim": fake.sentences(nb=3),
            "orphanet": fake.sentences(nb=3),
            "hpo": fake.sentences(nb=3),
            "old_panels": fake.sentences(nb=3),
            "status": GenePanel.STATUS.internal,
            "child_panels": [child1.pk, child2.pk],
        }

        url = reverse_lazy("panels:update", kwargs={"pk": parent.panel_id})
        res = self.client.post(url, new_data)

        self.assertEqual(parent.panel.active_panel.child_panels.count(), 2)
        self.assertEqual(len(parent.panel.active_panel.get_all_entities_extra), 3)

    def test_increment_child_version(self):
        gene1 = GeneFactory()
        gene2 = GeneFactory()
        parent = GenePanelSnapshotFactory(panel__status=GenePanel.STATUS.public)

        gene1_data = {
            "gene": gene1.pk,
            "sources": [Evidence.OTHER_SOURCES[0]],
            "phenotypes": fake.sentences(nb=3),
            "rating": Evaluation.RATINGS.AMBER,
            "moi": [x for x in Evaluation.MODES_OF_INHERITANCE][randint(1, 12)][0],
            "mode_of_pathogenicity": [x for x in Evaluation.MODES_OF_PATHOGENICITY][
                randint(1, 2)
            ][0],
            "penetrance": GenePanelEntrySnapshot.PENETRANCE.Incomplete,
            "current_diagnostic": False,
        }

        gene2_data = {
            "gene": gene2.pk,
            "sources": [Evidence.OTHER_SOURCES[0]],
            "phenotypes": fake.sentences(nb=3),
            "rating": Evaluation.RATINGS.AMBER,
            "moi": [x for x in Evaluation.MODES_OF_INHERITANCE][randint(1, 12)][0],
            "mode_of_pathogenicity": [x for x in Evaluation.MODES_OF_PATHOGENICITY][
                randint(1, 2)
            ][0],
            "penetrance": GenePanelEntrySnapshot.PENETRANCE.Incomplete,
            "current_diagnostic": False,
        }

        child1 = GenePanelSnapshotFactory(panel__status=GenePanel.STATUS.public)
        initial_child1_pk = child1.pk
        child1.add_gene(self.gel_user, gene1.gene_symbol, gene1_data)
        child1 = child1.panel.active_panel
        child1.add_gene(self.gel_user, gene2.gene_symbol, gene2_data)
        child1 = child1.panel.active_panel
        self.assertEqual(initial_child1_pk, child1.pk)

        child2 = GenePanelSnapshotFactory(panel__status=GenePanel.STATUS.public)
        initial_child2_pk = child2.pk
        child2.add_gene(self.gel_user, gene1.gene_symbol, gene1_data)
        child2 = child2.panel.active_panel

        self.assertEqual(initial_child2_pk, child2.pk)

        parent.child_panels.set([child1, child2])
        parent._update_saved_stats()
        old_parent = parent

        child1.increment_version(user=self.gel_user)
        child1 = child1.panel.active_panel
        child1.update_gene(
            self.gel_user,
            gene2.gene_symbol,
            {
                "gene": gene2,
                "sources": [Evidence.OTHER_SOURCES[1]],
                "phenotypes": fake.sentences(nb=3),
                "rating": Evaluation.RATINGS.GREEN,
                "moi": [x for x in Evaluation.MODES_OF_INHERITANCE][randint(1, 12)][0],
                "mode_of_pathogenicity": [x for x in Evaluation.MODES_OF_PATHOGENICITY][
                    randint(1, 2)
                ][0],
                "penetrance": GenePanelEntrySnapshot.PENETRANCE.Incomplete,
                "current_diagnostic": False,
            },
        )
        child1.get_gene(gene2.gene_symbol).update_rating(3, self.gel_user, "")
        child1 = child1.panel.active_panel
        parent = parent.panel.active_panel
        parent._update_saved_stats()

        self.assertNotEqual(old_parent.stats, parent.stats)
        self.assertIn(child1, parent.child_panels.all())
        self.assertIn(child2, parent.child_panels.all())
        self.assertEqual(child1.genepanelsnapshot_set.count(), 1)
        self.assertEqual(
            child2.genepanelsnapshot_set.count(), 1
        )  # contains reference to two versions of parent panel

    def test_multiple_parent_panels(self):
        """
        Test updates to the test panels, and make sure parent panels are updated correctly
        """
        gene1 = GeneFactory()
        gene2 = GeneFactory()
        gene3 = GeneFactory()

        gene1_data = {
            "gene": gene1.pk,
            "sources": [Evidence.OTHER_SOURCES[0]],
            "phenotypes": fake.sentences(nb=3),
            "rating": Evaluation.RATINGS.AMBER,
            "moi": [x for x in Evaluation.MODES_OF_INHERITANCE][randint(1, 12)][0],
            "mode_of_pathogenicity": [x for x in Evaluation.MODES_OF_PATHOGENICITY][
                randint(1, 2)
            ][0],
            "penetrance": GenePanelEntrySnapshot.PENETRANCE.Incomplete,
            "current_diagnostic": False,
        }

        gene2_data = {
            "gene": gene2.pk,
            "sources": [Evidence.OTHER_SOURCES[2]],
            "phenotypes": fake.sentences(nb=3),
            "rating": Evaluation.RATINGS.AMBER,
            "moi": [x for x in Evaluation.MODES_OF_INHERITANCE][randint(1, 12)][0],
            "mode_of_pathogenicity": [x for x in Evaluation.MODES_OF_PATHOGENICITY][
                randint(1, 2)
            ][0],
            "penetrance": GenePanelEntrySnapshot.PENETRANCE.Incomplete,
            "current_diagnostic": False,
        }

        gene3_data = {
            "gene": gene3.pk,
            "sources": [Evidence.OTHER_SOURCES[3]],
            "phenotypes": fake.sentences(nb=3),
            "rating": Evaluation.RATINGS.GREEN,
            "moi": [x for x in Evaluation.MODES_OF_INHERITANCE][randint(1, 12)][0],
            "mode_of_pathogenicity": [x for x in Evaluation.MODES_OF_PATHOGENICITY][
                randint(1, 2)
            ][0],
            "penetrance": GenePanelEntrySnapshot.PENETRANCE.Incomplete,
            "current_diagnostic": True,
        }

        child1 = GenePanelSnapshotFactory(panel__status=GenePanel.STATUS.public)
        child2 = GenePanelSnapshotFactory(panel__status=GenePanel.STATUS.public)
        child3 = GenePanelSnapshotFactory(panel__status=GenePanel.STATUS.public)

        parent = GenePanelSnapshotFactory(panel__status=GenePanel.STATUS.public)
        parent.child_panels.set([child1, child2])
        parent._update_saved_stats()
        self.assertEqual(parent.version, "0.0")

        parent2 = GenePanelSnapshotFactory(panel__status=GenePanel.STATUS.public)
        parent2.child_panels.set([child2, child3])
        parent2._update_saved_stats()
        self.assertEqual(parent2.version, "0.0")

        child1.add_gene(self.gel_user, gene1.gene_symbol, gene1_data)
        child1.add_gene(self.gel_user, gene2.gene_symbol, gene2_data)
        self.assertEqual(child1.version, "0.2")

        parent = parent.panel.active_panel
        self.assertEqual(parent.version, "0.2")

        parent2 = parent2.panel.active_panel
        self.assertEqual(parent2.version, "0.0")

        child2.add_gene(self.gel_user, gene2.gene_symbol, gene2_data)
        del child2.panel.active_panel
        child2 = child2.panel.active_panel
        self.assertEqual(child2.version, "0.1")

        del parent.panel.active_panel
        parent = parent.panel.active_panel
        self.assertEqual(parent.version, "0.3")

        del parent2.panel.active_panel
        parent2 = parent2.panel.active_panel
        self.assertEqual(parent2.version, "0.1")

        child3.add_gene(self.gel_user, gene3.gene_symbol, gene3_data)
        self.assertEqual(child3.version, "0.1")

        del parent.panel.active_panel
        parent = parent.panel.active_panel
        old_stats = parent.stats
        self.assertEqual(parent.version, "0.3")

        del parent2.panel.active_panel
        parent2 = parent2.panel.active_panel
        self.assertEqual(parent2.version, "0.2")

        child2.increment_version(user=self.gel_user)
        child2.update_gene(
            self.gel_user,
            gene2.gene_symbol,
            {
                "gene": gene2,
                "sources": [Evidence.OTHER_SOURCES[1]],
                "phenotypes": fake.sentences(nb=2),
                "rating": Evaluation.RATINGS.GREEN,
                "moi": [x for x in Evaluation.MODES_OF_INHERITANCE][randint(1, 12)][0],
                "mode_of_pathogenicity": [x for x in Evaluation.MODES_OF_PATHOGENICITY][
                    randint(1, 2)
                ][0],
                "penetrance": GenePanelEntrySnapshot.PENETRANCE.Incomplete,
                "current_diagnostic": True,
            },
        ).update_rating(3, self.gel_user, "")
        child2._update_saved_stats()

        self.assertEqual(child1.version, "0.2")
        self.assertEqual(child2.version, "0.2")
        self.assertEqual(child3.version, "0.1")

        del parent.panel.active_panel
        parent = parent.panel.active_panel
        self.assertEqual(parent.version, "0.4")
        self.assertNotEqual(old_stats, parent.stats)

        del parent2.panel.active_panel
        parent2 = parent2.panel.active_panel
        self.assertEqual(parent2.version, "0.3")
