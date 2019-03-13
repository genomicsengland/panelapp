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
from random import choice
from accounts.tests.setup import LoginGELUser
from accounts.tests.setup import LoginReviewerUser
from panels.models import GenePanelEntrySnapshot
from panels.models import Region
from panels.models import GenePanelSnapshot
from panels.models import Evidence
from panels.models import GenePanel
from panels.models import Evaluation
from panels.tests.factories import GeneFactory
from panels.tests.factories import RegionFactory
from panels.tests.factories import GenePanelSnapshotFactory
from panels.tests.factories import GenePanelEntrySnapshotFactory
from panels.tests.factories import TagFactory
from panels.tests.factories import CommentFactory


fake = Factory.create()


class GenePanelSnapshotReviewerTest(LoginReviewerUser):
    """Verified reviewer tests"""

    def test_reviewer_gene_grey(self):
        """When a reviewer adds a gene it should be marked as grey gene"""

        gene = GeneFactory()
        gps = GenePanelSnapshotFactory()
        url = reverse_lazy('panels:add_entity', kwargs={'pk': gps.panel.pk, 'entity_type': 'gene'})
        gene_data = {
            "gene": gene.pk,
            "source": Evidence.OTHER_SOURCES[0],
            "phenotypes": "{};{};{}".format(*fake.sentences(nb=3)),
            "rating": Evaluation.RATINGS.AMBER,
            "moi": [x for x in Evaluation.MODES_OF_INHERITANCE][randint(1, 12)][0],
            "mode_of_pathogenicity": [x for x in Evaluation.MODES_OF_PATHOGENICITY][randint(1, 2)][0],
            "penetrance": GenePanelEntrySnapshot.PENETRANCE.Incomplete,
        }
        self.client.post(url, gene_data)
        panel = gps.panel.active_panel

        self.assertEqual(panel.get_gene(gene.gene_symbol).saved_gel_status, 0)

    def test_reviewer_source_visible(self):
        """When a reviewer adds a gene source should be displayed"""

        gene = GeneFactory()
        gps = GenePanelSnapshotFactory()
        url = reverse_lazy('panels:add_entity', kwargs={'pk': gps.panel.pk, 'entity_type': 'gene'})
        gene_data = {
            "gene": gene.pk,
            "source": Evidence.OTHER_SOURCES[2],
            "phenotypes": "{};{};{}".format(*fake.sentences(nb=3)),
            "rating": Evaluation.RATINGS.AMBER,
            "moi": [x for x in Evaluation.MODES_OF_INHERITANCE][randint(1, 12)][0],
            "mode_of_pathogenicity": [x for x in Evaluation.MODES_OF_PATHOGENICITY][randint(1, 2)][0],
            "penetrance": GenePanelEntrySnapshot.PENETRANCE.Incomplete,
        }
        self.client.post(url, gene_data)

        url = reverse_lazy('panels:detail', kwargs={'pk': gps.panel.pk})
        res = self.client.get(url)
        self.assertContains(res, gene_data['source'])

    def test_add_gene_to_panel(self):
        """When a reviewer adds a gene it shouldn't increment the version of a panel"""

        gene = GeneFactory()
        gps = GenePanelSnapshotFactory()
        url = reverse_lazy('panels:add_entity', kwargs={'pk': gps.panel.pk, 'entity_type': 'gene'})
        gene_data = {
            "gene": gene.pk,
            "source": Evidence.OTHER_SOURCES[0],
            "phenotypes": "{};{};{}".format(*fake.sentences(nb=3)),
            "rating": Evaluation.RATINGS.AMBER,
            "moi": [x for x in Evaluation.MODES_OF_INHERITANCE][randint(1, 12)][0],
            "mode_of_pathogenicity": [x for x in Evaluation.MODES_OF_PATHOGENICITY][randint(1, 2)][0],
            "penetrance": GenePanelEntrySnapshot.PENETRANCE.Incomplete,
        }
        self.client.post(url, gene_data)
        panel = gps.panel.active_panel

        assert panel.version == gps.version


class GenePanelSnapshotTest(LoginGELUser):
    """GeL currator tests"""

    def test_add_gene_to_panel(self):
        gene = GeneFactory()
        gps = GenePanelSnapshotFactory()

        number_of_genes = gps.stats.get('number_of_genes', 0)

        url = reverse_lazy('panels:add_entity', kwargs={'pk': gps.panel.pk, 'entity_type': 'gene'})
        gene_data = {
            "gene": gene.pk,
            "source": Evidence.ALL_SOURCES[randint(0, 9)],
            "tags": [TagFactory().pk, ],
            "publications": "{};{};{}".format(*fake.sentences(nb=3)),
            "phenotypes": "{};{};{}".format(*fake.sentences(nb=3)),
            "rating": Evaluation.RATINGS.AMBER,
            "comments": fake.sentence(),
            "moi": [x for x in Evaluation.MODES_OF_INHERITANCE][randint(1, 12)][0],
            "mode_of_pathogenicity": [x for x in Evaluation.MODES_OF_PATHOGENICITY][randint(1, 2)][0],
            "penetrance": GenePanelEntrySnapshot.PENETRANCE.Incomplete,
            "current_diagnostic": "True"
        }
        res = self.client.post(url, gene_data)

        new_current_number = gps.panel.active_panel.stats.get('number_of_genes', 0)

        assert gps.panel.active_panel.version != gps.version

        assert res.status_code == 302
        assert number_of_genes + 1 == new_current_number

    def test_gel_curator_gene_red(self):
        """When gene is added by a GeL currator it should be marked as red"""

        gene = GeneFactory()
        gps = GenePanelSnapshotFactory()
        url = reverse_lazy('panels:add_entity', kwargs={'pk': gps.panel.pk, 'entity_type': 'gene'})
        gene_data = {
            "gene": gene.pk,
            "source": Evidence.OTHER_SOURCES[0],
            "phenotypes": "{};{};{}".format(*fake.sentences(nb=3)),
            "rating": Evaluation.RATINGS.AMBER,
            "moi": [x for x in Evaluation.MODES_OF_INHERITANCE][randint(1, 12)][0],
            "mode_of_pathogenicity": [x for x in Evaluation.MODES_OF_PATHOGENICITY][randint(1, 2)][0],
            "penetrance": GenePanelEntrySnapshot.PENETRANCE.Incomplete,
        }
        self.client.post(url, gene_data)
        panel = gps.panel.active_panel

        assert panel.get_gene(gene.gene_symbol).saved_gel_status == 1

    def test_gene_evaluation(self):
        gpes = GenePanelEntrySnapshotFactory()
        url = reverse_lazy('panels:evaluation', kwargs={
            'pk': gpes.panel.panel.pk,
            'entity_type': 'gene',
            'entity_name': gpes.gene.get('gene_symbol')
        })
        res = self.client.get(url)
        assert res.status_code == 200

    def test_edit_gene_in_panel(self):
        gpes = GenePanelEntrySnapshotFactory()
        url = reverse_lazy('panels:edit_entity', kwargs={
            'pk': gpes.panel.panel.pk,
            'entity_type': 'gene',
            'entity_name': gpes.gene.get('gene_symbol')
        })

        number_of_genes = gpes.panel.stats.get('number_of_genes')

        # make sure new data has at least 1 of the same items
        source = gpes.evidence.last().name

        publication = gpes.publications[0]
        phenotype = gpes.publications[1]

        new_evidence = Evidence.ALL_SOURCES[randint(0, 9)]
        original_evidences = set([ev.name for ev in gpes.evidence.all()])
        original_evidences.add(new_evidence)

        gene_data = {
            "gene": gpes.gene_core.pk,
            "gene_name": "Gene name",
            "source": set([source, new_evidence]),
            "tags": [TagFactory().pk, ] + [tag.pk for tag in gpes.tags.all()],
            "publications": ";".join([publication, fake.sentence()]),
            "phenotypes": ";".join([phenotype, fake.sentence(), fake.sentence()]),
            "moi": [x for x in Evaluation.MODES_OF_INHERITANCE][randint(1, 12)][0],
            "mode_of_pathogenicity": [x for x in Evaluation.MODES_OF_PATHOGENICITY][randint(1, 2)][0],
            "penetrance": GenePanelEntrySnapshot.PENETRANCE.Incomplete,
        }
        res = self.client.post(url, gene_data)
        assert res.status_code == 302
        gene = GenePanel.objects.get(pk=gpes.panel.panel.pk).active_panel.get_gene(gpes.gene_core.gene_symbol)
        assert gpes.panel.panel.active_panel.version != gpes.panel.version
        new_current_number = gpes.panel.panel.active_panel.stats.get('number_of_genes', 0)
        assert number_of_genes == new_current_number

    def test_remove_sources(self):
        """Remove sources via edit gene detail section"""

        gpes = GenePanelEntrySnapshotFactory(
            penetrance=GenePanelEntrySnapshot.PENETRANCE.Incomplete
        )
        url = reverse_lazy('panels:edit_entity', kwargs={
            'pk': gpes.panel.panel.pk,
            'entity_type': 'gene',
            'entity_name': gpes.gene.get('gene_symbol')
        })

        gene_data = {
            "gene": gpes.gene_core.pk,
            "gene_name": "Gene name",
            "source": set([ev.name for ev in gpes.evidence.all()[1:]]),
            "tags": [tag.pk for tag in gpes.tags.all()],
            "publications": ";".join([publication for publication in gpes.publications]),
            "phenotypes": ";".join([phenotype for phenotype in gpes.phenotypes]),
            "moi": gpes.moi,
            "mode_of_pathogenicity": gpes.mode_of_pathogenicity,
            "penetrance": GenePanelEntrySnapshot.PENETRANCE.Complete,
        }
        res = self.client.post(url, gene_data)
        assert res.status_code == 302
        gene = GenePanel.objects.get(pk=gpes.panel.panel.pk).active_panel.get_gene(gpes.gene_core.gene_symbol)
        assert gene.penetrance != gpes.penetrance

    def test_add_tag_via_edit_details(self):
        """Set tags via edit gene detail section"""

        gpes = GenePanelEntrySnapshotFactory(
            penetrance=GenePanelEntrySnapshot.PENETRANCE.Incomplete
        )
        url = reverse_lazy('panels:edit_entity', kwargs={
            'pk': gpes.panel.panel.pk,
            'entity_type': 'gene',
            'entity_name': gpes.gene.get('gene_symbol')
        })

        tag = TagFactory(name='some tag')

        gene_data = {
            "gene": gpes.gene_core.pk,
            "gene_name": "Gene name",
            "source": set([ev.name for ev in gpes.evidence.all()]),
            "tags": [tag.pk for tag in gpes.tags.all()] + [tag.pk,],
            "publications": ";".join([publication for publication in gpes.publications]),
            "phenotypes": ";".join([phenotype for phenotype in gpes.phenotypes]),
            "moi": gpes.moi,
            "mode_of_pathogenicity": gpes.mode_of_pathogenicity,
            "penetrance": GenePanelEntrySnapshot.PENETRANCE.Complete,
        }
        res = self.client.post(url, gene_data)
        assert res.status_code == 302
        gene = GenePanel.objects.get(pk=gpes.panel.panel.pk).active_panel.get_gene(gpes.gene_core.gene_symbol)
        assert sorted(list(gene.tags.values_list('pk'))) != sorted(list(gpes.tags.values_list('pk')))

    def test_remove_tag_via_edit_details(self):
        """Remove tags via edit gene detail section"""

        gpes = GenePanelEntrySnapshotFactory(
            penetrance=GenePanelEntrySnapshot.PENETRANCE.Incomplete
        )

        tag = TagFactory(name='some tag')
        gpes.tags.add(tag)

        url = reverse_lazy('panels:edit_entity', kwargs={
            'pk': gpes.panel.panel.pk,
            'entity_type': 'gene',
            'entity_name': gpes.gene.get('gene_symbol')
        })

        gene_data = {
            "gene": gpes.gene_core.pk,
            "gene_name": "Gene name",
            "source": set([ev.name for ev in gpes.evidence.all()]),
            "tags": [],
            "publications": ";".join([publication for publication in gpes.publications]),
            "phenotypes": ";".join([phenotype for phenotype in gpes.phenotypes]),
            "moi": gpes.moi,
            "mode_of_pathogenicity": gpes.mode_of_pathogenicity,
            "penetrance": GenePanelEntrySnapshot.PENETRANCE.Complete,
        }
        res = self.client.post(url, gene_data)
        assert res.status_code == 302
        gene = GenePanel.objects.get(pk=gpes.panel.panel.pk).active_panel.get_gene(gpes.gene_core.gene_symbol)
        assert list(gene.tags.all()) == []

    def test_change_penetrance(self):
        """Test if a curator can change Gene penetrance"""

        gpes = GenePanelEntrySnapshotFactory(
            penetrance=GenePanelEntrySnapshot.PENETRANCE.Incomplete
        )

        comment = CommentFactory(user=self.verified_user)
        gpes.comments.add(comment)

        url = reverse_lazy('panels:edit_entity', kwargs={
            'pk': gpes.panel.panel.pk,
            'entity_type': 'gene',
            'entity_name': gpes.gene.get('gene_symbol')
        })

        gene_data = {
            "gene": gpes.gene_core.pk,
            "gene_name": "Gene name",
            "source": set([ev.name for ev in gpes.evidence.all()]),
            "tags": [tag.pk for tag in gpes.tags.all()],
            "publications": ";".join([publication for publication in gpes.publications]),
            "phenotypes": ";".join([phenotype for phenotype in gpes.phenotypes]),
            "moi": gpes.moi,
            "mode_of_pathogenicity": gpes.mode_of_pathogenicity,
            "penetrance": GenePanelEntrySnapshot.PENETRANCE.Complete,
        }
        res = self.client.post(url, gene_data)
        assert res.status_code == 302
        gene = GenePanel.objects.get(pk=gpes.panel.panel.pk).active_panel.get_gene(gpes.gene_core.gene_symbol)
        assert gene.penetrance != gpes.penetrance

    def test_add_publication(self):
        """Add a publication to a gene panel entry"""

        gpes = GenePanelEntrySnapshotFactory(
            penetrance=GenePanelEntrySnapshot.PENETRANCE.Incomplete
        )
        gpes.publications = []
        gpes.save()

        url = reverse_lazy('panels:edit_entity', kwargs={
            'pk': gpes.panel.panel.pk,
            'entity_type': 'gene',
            'entity_name': gpes.gene.get('gene_symbol')
        })

        gene_data = {
            "gene": gpes.gene_core.pk,
            "gene_name": "Gene name",
            "source": set([ev.name for ev in gpes.evidence.all()]),
            "tags": [tag.pk for tag in gpes.tags.all()],
            "publications": ";".join([fake.sentence(), fake.sentence()]),
            "phenotypes": ";".join([phenotype for phenotype in gpes.phenotypes]),
            "moi": gpes.moi,
            "mode_of_pathogenicity": gpes.mode_of_pathogenicity,
            "penetrance": GenePanelEntrySnapshot.PENETRANCE.Complete,
        }
        res = self.client.post(url, gene_data)
        assert res.status_code == 302
        gene = GenePanel.objects.get(pk=gpes.panel.panel.pk).active_panel.get_gene(gpes.gene_core.gene_symbol)
        assert gene.publications != gpes.publications

    def test_remove_publication(self):
        """Remove a publication to a gene panel entry"""

        gpes = GenePanelEntrySnapshotFactory(
            penetrance=GenePanelEntrySnapshot.PENETRANCE.Incomplete
        )
        gpes.publications = [fake.sentence(), fake.sentence()]
        gpes.save()

        url = reverse_lazy('panels:edit_entity', kwargs={
            'pk': gpes.panel.panel.pk,
            'entity_type': 'gene',
            'entity_name': gpes.gene.get('gene_symbol')
        })

        gene_data = {
            "gene": gpes.gene_core.pk,
            "gene_name": "Gene name",
            "source": set([ev.name for ev in gpes.evidence.all()]),
            "tags": [tag.pk for tag in gpes.tags.all()],
            "publications": ";".join(gpes.publications[:1]),
            "phenotypes": ";".join([phenotype for phenotype in gpes.phenotypes]),
            "moi": gpes.moi,
            "mode_of_pathogenicity": gpes.mode_of_pathogenicity,
            "penetrance": GenePanelEntrySnapshot.PENETRANCE.Complete,
        }
        res = self.client.post(url, gene_data)
        assert res.status_code == 302
        gene = GenePanel.objects.get(pk=gpes.panel.panel.pk).active_panel.get_gene(gpes.gene_core.gene_symbol)
        assert gene.publications == gpes.publications[:1]

    def test_mitochondrial_gene(self):
        gene = GeneFactory(gene_symbol="MT-LORUM")
        gpes = GenePanelEntrySnapshotFactory(gene_core=gene)
        url = reverse_lazy('panels:edit_entity', kwargs={
            'pk': gpes.panel.panel.pk,
            'entity_type': 'gene',
            'entity_name': gpes.gene.get('gene_symbol')
        })

        # make sure new data has at least 1 of the same items

        gpes.publications[0]
        gpes.publications[1]

        gene_data = {
            "gene": gpes.gene_core.pk,
            "gene_name": "Gene name",
            "source": [ev.name for ev in gpes.evidence.all()],
            "tags": [TagFactory().pk, ] + [tag.pk for tag in gpes.tags.all()],
            "publications": ";".join(gpes.publications),
            "phenotypes": ";".join(gpes.phenotypes),
            "moi": gpes.moi,
            "mode_of_pathogenicity": [x for x in Evaluation.MODES_OF_PATHOGENICITY][randint(1, 2)][0],
            "penetrance": GenePanelEntrySnapshot.PENETRANCE.Incomplete,
        }
        res = self.client.post(url, gene_data)
        assert res.status_code == 302
        gene = GenePanel.objects.get(pk=gpes.panel.panel.pk).active_panel.get_gene(gpes.gene_core.gene_symbol)
        assert gene.moi == "MITOCHONDRIAL"

    def test_edit_gene_name_unit(self):
        gpes = GenePanelEntrySnapshotFactory()
        old_gene_symbol = gpes.gene.get('gene_symbol')
        new_gene = GeneFactory()

        ap = GenePanel.objects.get(pk=gpes.panel.panel.pk).active_panel

        assert ap.has_gene(old_gene_symbol) is True
        new_data = {
            "gene": new_gene,
            "gene_name": "Other name"
        }
        ap.update_gene(self.verified_user, old_gene_symbol, new_data)

        new_ap = GenePanel.objects.get(pk=gpes.panel.panel.pk).active_panel
        assert new_ap.has_gene(old_gene_symbol) is False
        assert new_ap.has_gene(new_gene.gene_symbol) is True

    def test_update_gene_preserves_comments_order(self):
        gpes = GenePanelEntrySnapshotFactory()
        comments = list(CommentFactory.create_batch(4, user=self.verified_user))

        for ev in gpes.evaluation.all():
            ev.comments.add(comments.pop())

        max_comments_num = max([e.comments.count() for e in gpes.evaluation.all()])
        self.assertEqual(1, max_comments_num)

        old_gene_symbol = gpes.gene.get('gene_symbol')
        new_gene = GeneFactory()
        ap = GenePanel.objects.get(pk=gpes.panel.panel.pk).active_panel

        new_data = {
            "gene": new_gene,
            "gene_name": "Other name"
        }
        ap.update_gene(self.verified_user, old_gene_symbol, new_data)

        new_ap = GenePanel.objects.get(pk=gpes.panel.panel.pk).active_panel
        gpes = new_ap.get_gene(new_gene.gene_symbol)

        max_comments_num_after_update = max([e.comments.count() for e in gpes.evaluation.all()])
        self.assertEqual(1, max_comments_num_after_update)

    def test_edit_gene_name_ajax(self):
        gpes = GenePanelEntrySnapshotFactory()
        url = reverse_lazy('panels:edit_entity', kwargs={
            'pk': gpes.panel.panel.pk,
            'entity_type': 'gene',
            'entity_name': gpes.gene.get('gene_symbol')
        })

        old_gene_symbol = gpes.gene.get('gene_symbol')

        # make sure new data has at least 1 of the same items
        source = gpes.evidence.last().name
        publication = gpes.publications[0]
        phenotype = gpes.publications[1]

        new_gene = GeneFactory()

        gene_data = {
            "gene": new_gene.pk,
            "gene_name": "Other name",
            "source": set([source, Evidence.ALL_SOURCES[randint(0, 9)]]),
            "tags": [TagFactory().pk, ] + [tag.pk for tag in gpes.tags.all()],
            "publications": ";".join([publication, fake.sentence()]),
            "phenotypes": ";".join([phenotype, fake.sentence(), fake.sentence()]),
            "moi": [x for x in Evaluation.MODES_OF_INHERITANCE][randint(1, 12)][0],
            "mode_of_pathogenicity": [x for x in Evaluation.MODES_OF_PATHOGENICITY][randint(1, 2)][0],
            "penetrance": GenePanelEntrySnapshot.PENETRANCE.Incomplete,
        }
        res = self.client.post(url, gene_data)
        assert res.status_code == 302

        new_gps = GenePanel.objects.get(pk=gpes.panel.panel.pk).active_panel
        old_gps = GenePanelSnapshot.objects.get(pk=gpes.panel.pk)

        # check panel has no previous gene
        assert new_gps.has_gene(old_gene_symbol) is False

        # test previous panel contains old gene
        assert old_gps.has_gene(old_gene_symbol) is True

    def test_type_of_variants_added(self):
        region = RegionFactory()
        gps = GenePanelSnapshotFactory()
        url = reverse_lazy('panels:add_entity', kwargs={'pk': gps.panel.pk, 'entity_type': 'region'})

        source = region.evidence.last().name
        publication = region.publications[0]
        phenotype = region.publications[1]

        region_data = {
            'name': region.name,
            'chromosome': '1',
            'position_37_0': '12345',
            'position_37_1': '12346',
            'position_38_0': '12345',
            'position_38_1': '123456',
            'haploinsufficiency_score': choice(Region.DOSAGE_SENSITIVITY_SCORES)[0],
            'triplosensitivity_score': '',
            'required_overlap_percentage': randint(0, 100),
            "gene": region.gene_core.pk,
            "gene_name": "Other name",
            "source": set([source, Evidence.ALL_SOURCES[randint(0, 9)]]),
            "tags": [TagFactory().pk, ] + [tag.name for tag in region.tags.all()],
            "publications": ";".join([publication, fake.sentence()]),
            "phenotypes": ";".join([phenotype, fake.sentence(), fake.sentence()]),
            "moi": [x for x in Evaluation.MODES_OF_INHERITANCE][randint(1, 12)][0],
            "type_of_variants": Region.VARIANT_TYPES.small,
            "penetrance": Region.PENETRANCE.Incomplete,

        }
        res = self.client.post(url, region_data)
        self.assertEqual(res.status_code, 302)
        panel = gps.panel.active_panel

        assert panel.get_region(region.name).type_of_variants == region_data['type_of_variants']
