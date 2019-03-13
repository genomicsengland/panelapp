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
from random import choice
from django.urls import reverse_lazy
from faker import Factory
from accounts.tests.setup import LoginGELUser
from panels.models import GenePanel
from panels.models import GenePanelEntrySnapshot
from panels.models import Evaluation
from panels.models import Evidence
from panels.models import GenePanelSnapshot
from panels.models import Region
from panels.tests.factories import GeneFactory
from panels.tests.factories import GenePanelSnapshotFactory
from panels.tests.factories import GenePanelEntrySnapshotFactory
from panels.tests.factories import RegionFactory
from panels.tests.factories import TagFactory
from panels.tests.factories import CommentFactory


fake = Factory.create()


class RegionTest(LoginGELUser):
    def test_region_data_copied(self):
        gpes = GenePanelEntrySnapshotFactory()
        active_panel = gpes.panel
        region = active_panel.add_region(self.gel_user, 'ABC', {
            'gene': gpes.gene_core,
            'chromosome': '1',
            'position_37': None,
            'position_38': (12345, 12346),
            'haploinsufficiency_score': choice(Region.DOSAGE_SENSITIVITY_SCORES)[0],
            'triplosensitivity_score': choice(Region.DOSAGE_SENSITIVITY_SCORES)[0],
            'required_overlap_percentage': randint(0, 100),
            'panel': active_panel,
            'moi': 'X-LINKED: hemizygous mutation in males, biallelic mutations in females',
            'penetrance': 'Incomplete',
            'publications': None,
            'phenotypes': None,
            'sources': [],
            "type_of_variants": Region.VARIANT_TYPES.small,
        })

        active_panel = active_panel.panel.active_panel
        assert active_panel.has_region(region.name)
        active_panel.increment_version()
        assert active_panel.panel.active_panel.has_region(region.name)

    def test_add_region_to_panel(self):
        gene = GeneFactory()
        gps = GenePanelSnapshotFactory()

        number_of_regions = gps.stats.get('number_of_regions')

        url = reverse_lazy('panels:add_entity', kwargs={'pk': gps.panel.pk, 'entity_type': 'region'})
        region_data = {
            'name': 'SomeRegion',
            'chromosome': '1',
            'position_37_0': '',
            'position_37_1': '',
            'position_38_0': '12345',
            'position_38_1': '123456',
            'haploinsufficiency_score': choice(Region.DOSAGE_SENSITIVITY_SCORES)[0],
            'triplosensitivity_score': choice(Region.DOSAGE_SENSITIVITY_SCORES)[0],
            'required_overlap_percentage': randint(0, 100),
            "gene": gene.pk,
            "source": Evidence.ALL_SOURCES[randint(0, 9)],
            "tags": [TagFactory().pk, ],
            "publications": "{};{};{}".format(*fake.sentences(nb=3)),
            "phenotypes": "{};{};{}".format(*fake.sentences(nb=3)),
            "rating": Evaluation.RATINGS.AMBER,
            "comments": fake.sentence(),
            "moi": [x for x in Evaluation.MODES_OF_INHERITANCE][randint(1, 12)][0],
            "penetrance": Region.PENETRANCE.Incomplete,
            "current_diagnostic": "True",
            "type_of_variants": Region.VARIANT_TYPES.small,
        }
        res = self.client.post(url, region_data)

        new_current_number = gps.panel.active_panel.stats.get('number_of_regions')

        assert gps.panel.active_panel.version != gps.version

        assert res.status_code == 302
        assert number_of_regions + 1 == new_current_number

        # make sure tags are added
        new_region = GenePanel.objects.get(pk=gps.panel.pk).active_panel.get_region(region_data['name'])
        assert sorted(list(new_region.tags.all().values_list('pk', flat=True))) == sorted(region_data['tags'])

    def test_add_region_to_panel_no_gene_data(self):
        """Regions can exist without genes"""

        gps = GenePanelSnapshotFactory()

        number_of_regions = gps.stats.get('number_of_regions')

        url = reverse_lazy('panels:add_entity', kwargs={'pk': gps.panel.pk, 'entity_type': 'region'})
        region_data = {
            'name': 'SomeRegion',
            'chromosome': '1',
            'position_37_0': '12345',
            'position_37_1': '12346',
            'position_38_0': '12345',
            'position_38_1': '123456',
            'haploinsufficiency_score': choice(Region.DOSAGE_SENSITIVITY_SCORES)[0],
            'triplosensitivity_score': choice(Region.DOSAGE_SENSITIVITY_SCORES)[0],
            'required_overlap_percentage': randint(0, 100),
            "source": Evidence.ALL_SOURCES[randint(0, 9)],
            "tags": [TagFactory().pk, ],
            "publications": "{};{};{}".format(*fake.sentences(nb=3)),
            "phenotypes": "{};{};{}".format(*fake.sentences(nb=3)),
            "rating": Evaluation.RATINGS.AMBER,
            "comments": fake.sentence(),
            "moi": [x for x in Evaluation.MODES_OF_INHERITANCE][randint(1, 12)][0],
            "penetrance": Region.PENETRANCE.Incomplete,
            "current_diagnostic": "True",
            "type_of_variants": Region.VARIANT_TYPES.small,
        }
        res = self.client.post(url, region_data)

        new_current_number = gps.panel.active_panel.stats.get('number_of_regions')

        assert gps.panel.active_panel.version != gps.version

        assert res.status_code == 302
        assert number_of_regions + 1 == new_current_number

    def test_gel_curator_region_red(self):
        """When gene is added by a GeL currator it should be marked as red"""

        gene = GeneFactory()
        gps = GenePanelSnapshotFactory()
        url = reverse_lazy('panels:add_entity', kwargs={'pk': gps.panel.pk, 'entity_type': 'region'})
        region_data = {
            'name': 'SomeRegion',
            'chromosome': '1',
            'position_37_0': '12345',
            'position_37_1': '12346',
            'position_38_0': '12345',
            'position_38_1': '123456',
            'haploinsufficiency_score': choice(Region.DOSAGE_SENSITIVITY_SCORES)[0],
            'triplosensitivity_score': choice(Region.DOSAGE_SENSITIVITY_SCORES)[0],
            'required_overlap_percentage': randint(0, 100),
            "gene": gene.pk,
            "source": Evidence.OTHER_SOURCES[0],
            "phenotypes": "{};{};{}".format(*fake.sentences(nb=3)),
            "rating": Evaluation.RATINGS.AMBER,
            "moi": [x for x in Evaluation.MODES_OF_INHERITANCE][randint(1, 12)][0],
            "mode_of_pathogenicity": [x for x in Evaluation.MODES_OF_PATHOGENICITY][randint(1, 2)][0],
            "penetrance": Region.PENETRANCE.Incomplete,
            "type_of_variants": Region.VARIANT_TYPES.small,
        }
        self.client.post(url, region_data)
        panel = gps.panel.active_panel

        assert panel.get_region('SomeRegion').saved_gel_status == 1

    def test_region_evaluation(self):
        region = RegionFactory()
        url = reverse_lazy('panels:evaluation', kwargs={
            'pk': region.panel.panel.pk,
            'entity_type': 'region',
            'entity_name': region.name
        })
        res = self.client.get(url)
        assert res.status_code == 200

    def test_edit_region_in_panel(self):
        region = RegionFactory()
        url = reverse_lazy('panels:edit_entity', kwargs={
            'pk': region.panel.panel.pk,
            'entity_type': 'region',
            'entity_name': region.name
        })

        number_of_regions = region.panel.stats.get('number_of_regions')

        # make sure new data has at least 1 of the same items
        source = region.evidence.last().name

        publication = region.publications[0]
        phenotype = region.publications[1]

        new_evidence = Evidence.ALL_SOURCES[randint(0, 9)]
        original_evidences = set([ev.name for ev in region.evidence.all()])
        original_evidences.add(new_evidence)

        region_data = {
            'name': region.name,
            'chromosome': '1',
            'position_37_0': '12345',
            'position_37_1': '12346',
            'position_38_0': '12345',
            'position_38_1': '123456',
            'haploinsufficiency_score': choice(Region.DOSAGE_SENSITIVITY_SCORES)[0],
            'triplosensitivity_score': choice(Region.DOSAGE_SENSITIVITY_SCORES)[0],
            'required_overlap_percentage': randint(0, 100),
            "gene": region.gene_core.pk,
            "gene_name": "Gene name",
            "source": set([source, new_evidence]),
            "tags": [TagFactory().pk, ] + [tag.name for tag in region.tags.all()],
            "publications": ";".join([publication, fake.sentence()]),
            "phenotypes": ";".join([phenotype, fake.sentence(), fake.sentence()]),
            "moi": [x for x in Evaluation.MODES_OF_INHERITANCE][randint(1, 12)][0],
            "penetrance": Region.PENETRANCE.Incomplete,
            "type_of_variants": Region.VARIANT_TYPES.small,
        }
        res = self.client.post(url, region_data)
        assert res.status_code == 302
        new_region = GenePanel.objects.get(pk=region.panel.panel.pk).active_panel.get_region(region.name)
        assert region.panel.panel.active_panel.version != region.panel.version
        new_current_number = new_region.panel.panel.active_panel.stats.get('number_of_regions')
        assert number_of_regions == new_current_number
        self.assertEqual(int(region_data['position_37_1']), new_region.position_37.upper)

    def test_remove_gene_from_region(self):
        """We need ability to remove genes from Regions"""

        region = RegionFactory()
        url = reverse_lazy('panels:edit_entity', kwargs={
            'pk': region.panel.panel.pk,
            'entity_type': 'region',
            'entity_name': region.name
        })

        number_of_regions = region.panel.stats.get('number_of_regions')

        # make sure new data has at least 1 of the same items
        source = region.evidence.last().name

        publication = region.publications[0]
        phenotype = region.publications[1]

        new_evidence = Evidence.ALL_SOURCES[randint(0, 9)]
        original_evidences = set([ev.name for ev in region.evidence.all()])
        original_evidences.add(new_evidence)

        region_data = {
            'name': region.name,
            'chromosome': '1',
            'position_37_0': '12345',
            'position_37_1': '12346',
            'position_38_0': '12345',
            'position_38_1': '123456',
            'haploinsufficiency_score': choice(Region.DOSAGE_SENSITIVITY_SCORES)[0],
            'triplosensitivity_score': choice(Region.DOSAGE_SENSITIVITY_SCORES)[0],
            'required_overlap_percentage': randint(0, 100),
            "gene_name": "Gene name",
            "source": set([source, new_evidence]),
            "tags": [TagFactory().pk, ] + [tag.name for tag in region.tags.all()],
            "publications": ";".join([publication, fake.sentence()]),
            "phenotypes": ";".join([phenotype, fake.sentence(), fake.sentence()]),
            "moi": [x for x in Evaluation.MODES_OF_INHERITANCE][randint(1, 12)][0],
            "penetrance": Region.PENETRANCE.Incomplete,
            "type_of_variants": Region.VARIANT_TYPES.small,
        }
        res = self.client.post(url, region_data)
        assert res.status_code == 302
        new_region = GenePanel.objects.get(pk=region.panel.panel.pk).active_panel.get_region(region.name)
        assert not new_region.gene_core
        assert not new_region.gene
        assert region.panel.panel.active_panel.version != region.panel.version
        new_current_number = new_region.panel.panel.active_panel.stats.get('number_of_regions')
        assert number_of_regions == new_current_number

    def test_remove_sources(self):
        """Remove sources via edit gene detail section"""

        region = RegionFactory(
            penetrance=GenePanelEntrySnapshot.PENETRANCE.Incomplete
        )
        url = reverse_lazy('panels:edit_entity', kwargs={
            'pk': region.panel.panel.pk,
            'entity_type': 'region',
            'entity_name': region.name
        })

        region_data = {
            'name': region.name,
            'chromosome': '1',
            'position_37_0': '12345',
            'position_37_1': '12346',
            'position_38_0': '12345',
            'position_38_1': '123456',
            'haploinsufficiency_score': choice(Region.DOSAGE_SENSITIVITY_SCORES)[0],
            'triplosensitivity_score': choice(Region.DOSAGE_SENSITIVITY_SCORES)[0],
            'required_overlap_percentage': randint(0, 100),
            "gene": region.gene_core.pk,
            "gene_name": "Gene name",
            "source": set([ev.name for ev in region.evidence.all()[1:]]),
            "tags": [tag.name for tag in region.tags.all()],
            "publications": ";".join([publication for publication in region.publications]),
            "phenotypes": ";".join([phenotype for phenotype in region.phenotypes]),
            "moi": region.moi,
            "type_of_variants": Region.VARIANT_TYPES.small,
            "penetrance": Region.PENETRANCE.Complete,
        }
        res = self.client.post(url, region_data)
        assert res.status_code == 302
        new_region = GenePanel.objects.get(pk=region.panel.panel.pk).active_panel.get_region(region.name)
        assert new_region.penetrance != region.penetrance

    def test_add_tag_via_edit_details(self):
        """Set tags via edit gene detail section"""

        region = RegionFactory(
            penetrance=Region.PENETRANCE.Incomplete
        )
        url = reverse_lazy('panels:edit_entity', kwargs={
            'pk': region.panel.panel.pk,
            'entity_type': 'region',
            'entity_name': region.name
        })

        tag = TagFactory(name='some tag')

        region_data = {
            'name': region.name,
            'chromosome': '1',
            'position_37_0': '12345',
            'position_37_1': '12346',
            'position_38_0': '12345',
            'position_38_1': '123456',
            'haploinsufficiency_score': choice(Region.DOSAGE_SENSITIVITY_SCORES)[0],
            'triplosensitivity_score': choice(Region.DOSAGE_SENSITIVITY_SCORES)[0],
            'required_overlap_percentage': randint(0, 100),
            "gene": region.gene_core.pk,
            "gene_name": "Gene name",
            "source": set([ev.name for ev in region.evidence.all()]),
            "tags": [tag.pk for tag in region.tags.all()] + [tag.pk, ],
            "publications": ";".join([publication for publication in region.publications]),
            "phenotypes": ";".join([phenotype for phenotype in region.phenotypes]),
            "type_of_variants": Region.VARIANT_TYPES.small,
            "moi": region.moi,
            "penetrance": Region.PENETRANCE.Complete,
        }
        res = self.client.post(url, region_data)
        assert res.status_code == 302
        new_region = GenePanel.objects.get(pk=region.panel.panel.pk).active_panel.get_region(region.name)
        assert sorted(list(new_region.tags.all())) != sorted(list(region.tags.all()))

    def test_remove_tag_via_edit_details(self):
        """Remove tags via edit gene detail section"""

        region = RegionFactory(
            penetrance=Region.PENETRANCE.Incomplete
        )

        tag = TagFactory(name='some tag')
        region.tags.add(tag)

        url = reverse_lazy('panels:edit_entity', kwargs={
            'pk': region.panel.panel.pk,
            'entity_type': 'region',
            'entity_name': region.name
        })

        region_data = {
            'name': region.name,
            'chromosome': '1',
            'position_37_0': '12345',
            'position_37_1': '12346',
            'position_38_0': '12345',
            'position_38_1': '123456',
            'haploinsufficiency_score': choice(Region.DOSAGE_SENSITIVITY_SCORES)[0],
            'triplosensitivity_score': choice(Region.DOSAGE_SENSITIVITY_SCORES)[0],
            'required_overlap_percentage': randint(0, 100),
            "gene": region.gene_core.pk,
            "gene_name": "Gene name",
            "source": set([ev.name for ev in region.evidence.all()]),
            "tags": [],
            "publications": ";".join([publication for publication in region.publications]),
            "phenotypes": ";".join([phenotype for phenotype in region.phenotypes]),
            "type_of_variants": Region.VARIANT_TYPES.small,
            "moi": region.moi,
            "penetrance": Region.PENETRANCE.Complete,
        }
        res = self.client.post(url, region_data)
        assert res.status_code == 302
        new_region = GenePanel.objects.get(pk=region.panel.panel.pk).active_panel.get_region(region.name)
        assert list(new_region.tags.all()) == []

    def test_change_penetrance(self):
        """Test if a curator can change Gene penetrance"""

        region = RegionFactory(
            penetrance=Region.PENETRANCE.Incomplete
        )
        url = reverse_lazy('panels:edit_entity', kwargs={
            'pk': region.panel.panel.pk,
            'entity_type': 'region',
            'entity_name': region.name
        })

        region_data = {
            'name': region.name,
            'chromosome': '1',
            'position_37_0': '12345',
            'position_37_1': '12346',
            'position_38_0': '12345',
            'position_38_1': '123456',
            'haploinsufficiency_score': choice(Region.DOSAGE_SENSITIVITY_SCORES)[0],
            'triplosensitivity_score': choice(Region.DOSAGE_SENSITIVITY_SCORES)[0],
            'required_overlap_percentage': randint(0, 100),
            "gene": region.gene_core.pk,
            "gene_name": "Gene name",
            "source": set([ev.name for ev in region.evidence.all()]),
            "tags": [tag.name for tag in region.tags.all()],
            "publications": ";".join([publication for publication in region.publications]),
            "phenotypes": ";".join([phenotype for phenotype in region.phenotypes]),
            "type_of_variants": Region.VARIANT_TYPES.small,
            "moi": region.moi,
            "penetrance": Region.PENETRANCE.Complete,
        }
        res = self.client.post(url, region_data)
        assert res.status_code == 302
        new_region = GenePanel.objects.get(pk=region.panel.panel.pk).active_panel.get_region(region.name)
        assert new_region.penetrance != region.penetrance

    def test_add_publication(self):
        """Add a publication to a gene panel entry"""

        region = RegionFactory(
            penetrance=Region.PENETRANCE.Incomplete
        )
        region.publications = []
        region.save()

        url = reverse_lazy('panels:edit_entity', kwargs={
            'pk': region.panel.panel.pk,
            'entity_type': 'region',
            'entity_name': region.name
        })

        region_data = {
            'name': region.name,
            'chromosome': '1',
            'position_37_0': '12345',
            'position_37_1': '12346',
            'position_38_0': '12345',
            'position_38_1': '123456',
            'haploinsufficiency_score': choice(Region.DOSAGE_SENSITIVITY_SCORES)[0],
            'triplosensitivity_score': choice(Region.DOSAGE_SENSITIVITY_SCORES)[0],
            'required_overlap_percentage': randint(0, 100),
            "gene": region.gene_core.pk,
            "gene_name": "Gene name",
            "source": set([ev.name for ev in region.evidence.all()]),
            "tags": [tag.name for tag in region.tags.all()],
            "publications": ";".join([fake.sentence(), fake.sentence()]),
            "phenotypes": ";".join([phenotype for phenotype in region.phenotypes]),
            "type_of_variants": Region.VARIANT_TYPES.small,
            "moi": region.moi,
            "penetrance": Region.PENETRANCE.Complete,
        }

        res = self.client.post(url, region_data)
        assert res.status_code == 302
        new_region = GenePanel.objects.get(pk=region.panel.panel.pk).active_panel.get_region(region.name)
        assert new_region.publications != region.publications

    def test_remove_publication(self):
        """Remove a publication to a gene panel entry"""

        region = RegionFactory(
            penetrance=Region.PENETRANCE.Incomplete
        )
        region.publications = [fake.sentence(), fake.sentence()]
        region.save()

        url = reverse_lazy('panels:edit_entity', kwargs={
            'pk': region.panel.panel.pk,
            'entity_type': 'region',
            'entity_name': region.name
        })

        region_data = {
            'name': region.name,
            'chromosome': '1',
            'position_37_0': '12345',
            'position_37_1': '12346',
            'position_38_0': '12345',
            'position_38_1': '123456',
            'haploinsufficiency_score': choice(Region.DOSAGE_SENSITIVITY_SCORES)[0],
            'triplosensitivity_score': choice(Region.DOSAGE_SENSITIVITY_SCORES)[0],
            'required_overlap_percentage': randint(0, 100),
            "gene": region.gene_core.pk,
            "gene_name": "Gene name",
            "source": set([ev.name for ev in region.evidence.all()]),
            "tags": [tag.name for tag in region.tags.all()],
            "publications": ";".join(region.publications[:1]),
            "phenotypes": ";".join([phenotype for phenotype in region.phenotypes]),
            "type_of_variants": Region.VARIANT_TYPES.small,
            "moi": region.moi,
            "penetrance": Region.PENETRANCE.Complete,
        }
        res = self.client.post(url, region_data)
        assert res.status_code == 302
        new_region = GenePanel.objects.get(pk=region.panel.panel.pk).active_panel.get_region(region.name)
        assert new_region.publications == region.publications[:1]

    def test_edit_region_name_unit(self):
        region = RegionFactory()
        old_region_name = region.name

        ap = GenePanel.objects.get(pk=region.panel.panel.pk).active_panel

        assert ap.has_region(old_region_name) is True
        new_data = {
            "name": 'NewRegion'
        }
        ap.update_region(self.verified_user, old_region_name, new_data)

        new_ap = GenePanel.objects.get(pk=region.panel.panel.pk).active_panel
        assert new_ap.has_region(old_region_name) is False
        assert new_ap.has_region('NewRegion') is True

    def test_update_region_preserves_comments_order(self):
        region = RegionFactory()
        comments = list(CommentFactory.create_batch(4, user=self.verified_user))

        for ev in region.evaluation.all():
            ev.comments.add(comments.pop())

        max_comments_num = max([e.comments.count() for e in region.evaluation.all()])
        self.assertEqual(1, max_comments_num)

        old_region_name = region.name
        ap = GenePanel.objects.get(pk=region.panel.panel.pk).active_panel

        new_data = {
            "name": 'NewRegion'
        }
        ap.update_region(self.verified_user, old_region_name, new_data)

        new_ap = GenePanel.objects.get(pk=region.panel.panel.pk).active_panel
        new_region = new_ap.get_region('NewRegion')

        max_comments_num_after_update = max([e.comments.count() for e in new_region.evaluation.all()])
        self.assertEqual(1, max_comments_num_after_update)

    def test_edit_region_name_ajax(self):
        region = RegionFactory()
        url = reverse_lazy('panels:edit_entity', kwargs={
            'pk': region.panel.panel.pk,
            'entity_type': 'region',
            'entity_name': region.name
        })

        old_region_name = region.name

        # make sure new data has at least 1 of the same items
        source = region.evidence.last().name
        publication = region.publications[0]
        phenotype = region.publications[1]

        gene_data = {
            'name': 'NewRegion',
            'chromosome': '1',
            'position_37_0': '12345',
            'position_37_1': '12346',
            'position_38_0': '12345',
            'position_38_1': '123456',
            'haploinsufficiency_score': choice(Region.DOSAGE_SENSITIVITY_SCORES)[0],
            'triplosensitivity_score': choice(Region.DOSAGE_SENSITIVITY_SCORES)[0],
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
        res = self.client.post(url, gene_data)
        assert res.status_code == 302

        new_gps = GenePanel.objects.get(pk=region.panel.panel.pk).active_panel
        old_gps = GenePanelSnapshot.objects.get(pk=region.panel.pk)

        # check panel has no previous gene
        assert new_gps.has_region(old_region_name) is False

        # test previous panel contains old gene
        assert old_gps.has_region(old_region_name) is True

    def test_download_panel_contains_regions(self):
        gpes = GenePanelEntrySnapshotFactory()
        gps = gpes.panel
        RegionFactory(panel=gps)

        res = self.client.get(reverse_lazy('panels:download_panel_tsv', args=(gps.panel.pk, '01234')))
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.content.find(b'region') != 1)

    def test_download_all_regions(self):
        gpes = GenePanelEntrySnapshotFactory()
        gps = gpes.panel
        region = RegionFactory(panel=gps)

        res = self.client.get(reverse_lazy('panels:download_regions'))
        self.assertEqual(res.status_code, 200)
        self.assertTrue(b"".join(res.streaming_content).find(region.verbose_name.encode()) != 1)
