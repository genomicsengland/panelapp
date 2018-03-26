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
        str_item = active_panel.add_str(self.gel_user, 'ABC', {
            'gene': gpes.gene_core,
            'position_37': '1:12345',
            'position_38': '1:12345',
            'repeated_sequence': 'ATAT',
            'normal_range': (1, 2),
            'prepathogenic_range': (1, 2),
            'pathogenic_range': (1, 2),
            'panel': active_panel,
            'moi': 'X-LINKED: hemizygous mutation in males, biallelic mutations in females',
            'penetrance': 'Incomplete',
            'publications': None,
            'phenotypes': None,
            'sources': [],
        })

        assert active_panel.has_str(str_item.name)
        active_panel.increment_version()
        assert active_panel.panel.active_panel.has_str(str_item.name)

    def test_add_str_to_panel(self):
        gene = GeneFactory()
        gps = GenePanelSnapshotFactory()

        number_of_strs = gps.number_of_strs

        url = reverse_lazy('panels:add_entity', kwargs={'pk': gps.panel.pk, 'entity_type': 'str'})
        gene_data = {
            'name': 'SomeSTR',
            'position_37': '1:12345',
            'position_38': '1:12345',
            'repeated_sequence': 'ATAT',
            'normal_range_0': 1,
            'normal_range_1': 2,
            'prepathogenic_range_0': 1,
            'prepathogenic_range_1': 2,
            'pathogenic_range_0': 1,
            'pathogenic_range_1': 2,
            "gene": gene.pk,
            "source": Evidence.ALL_SOURCES[randint(0, 9)],
            "tags": [TagFactory().pk, ],
            "publications": "{};{};{}".format(*fake.sentences(nb=3)),
            "phenotypes": "{};{};{}".format(*fake.sentences(nb=3)),
            "rating": Evaluation.RATINGS.AMBER,
            "comments": fake.sentence(),
            "moi": [x for x in Evaluation.MODES_OF_INHERITANCE][randint(1, 12)][0],
            "penetrance": GenePanelEntrySnapshot.PENETRANCE.Incomplete,
            "current_diagnostic": "True"
        }
        res = self.client.post(url, gene_data)

        new_current_number = gps.panel.active_panel.number_of_strs

        assert gps.panel.active_panel.version != gps.version

        assert res.status_code == 302
        assert number_of_strs + 1 == new_current_number

    def test_add_str_to_panel_no_gene_data(self):
        """STRs can exist without genes"""

        gps = GenePanelSnapshotFactory()

        number_of_strs = gps.number_of_strs

        url = reverse_lazy('panels:add_entity', kwargs={'pk': gps.panel.pk, 'entity_type': 'str'})
        gene_data = {
            'name': 'SomeSTR',
            'position_37': '1:12345',
            'position_38': '1:12345',
            'repeated_sequence': 'ATAT',
            'normal_range_0': 1,
            'normal_range_1': 2,
            'prepathogenic_range_0': 1,
            'prepathogenic_range_1': 2,
            'pathogenic_range_0': 1,
            'pathogenic_range_1': 2,
            "source": Evidence.ALL_SOURCES[randint(0, 9)],
            "tags": [TagFactory().pk, ],
            "publications": "{};{};{}".format(*fake.sentences(nb=3)),
            "phenotypes": "{};{};{}".format(*fake.sentences(nb=3)),
            "rating": Evaluation.RATINGS.AMBER,
            "comments": fake.sentence(),
            "moi": [x for x in Evaluation.MODES_OF_INHERITANCE][randint(1, 12)][0],
            "penetrance": GenePanelEntrySnapshot.PENETRANCE.Incomplete,
            "current_diagnostic": "True"
        }
        res = self.client.post(url, gene_data)

        new_current_number = gps.panel.active_panel.number_of_strs

        assert gps.panel.active_panel.version != gps.version

        assert res.status_code == 302
        assert number_of_strs + 1 == new_current_number

    def test_gel_curator_str_red(self):
        """When gene is added by a GeL currator it should be marked as red"""

        gene = GeneFactory()
        gps = GenePanelSnapshotFactory()
        url = reverse_lazy('panels:add_entity', kwargs={'pk': gps.panel.pk, 'entity_type': 'str'})
        str_data = {
            'name': 'SomeSTR',
            'position_37': '1:12345',
            'position_38': '1:12345',
            'repeated_sequence': 'ATAT',
            'normal_range_0': 1,
            'normal_range_1': 2,
            'prepathogenic_range_0': 1,
            'prepathogenic_range_1': 2,
            'pathogenic_range_0': 1,
            'pathogenic_range_1': 2,
            "gene": gene.pk,
            "source": Evidence.OTHER_SOURCES[0],
            "phenotypes": "{};{};{}".format(*fake.sentences(nb=3)),
            "rating": Evaluation.RATINGS.AMBER,
            "moi": [x for x in Evaluation.MODES_OF_INHERITANCE][randint(1, 12)][0],
            "mode_of_pathogenicity": [x for x in Evaluation.MODES_OF_PATHOGENICITY][randint(1, 2)][0],
            "penetrance": GenePanelEntrySnapshot.PENETRANCE.Incomplete,
        }
        self.client.post(url, str_data)
        panel = gps.panel.active_panel

        assert panel.get_str('SomeSTR').saved_gel_status == 1

    def test_str_evaluation(self):
        str_item = STRFactory()
        url = reverse_lazy('panels:evaluation', kwargs={
            'pk': str_item.panel.panel.pk,
            'entity_type': 'str',
            'entity_name': str_item.name
        })
        res = self.client.get(url)
        assert res.status_code == 200

    def test_edit_str_in_panel(self):
        str_item = STRFactory()
        url = reverse_lazy('panels:edit_entity', kwargs={
            'pk': str_item.panel.panel.pk,
            'entity_type': 'str',
            'entity_name': str_item.name
        })

        number_of_strs = str_item.panel.number_of_strs

        # make sure new data has at least 1 of the same items
        source = str_item.evidence.last().name

        publication = str_item.publications[0]
        phenotype = str_item.publications[1]

        new_evidence = Evidence.ALL_SOURCES[randint(0, 9)]
        original_evidences = set([ev.name for ev in str_item.evidence.all()])
        original_evidences.add(new_evidence)

        str_data = {
            'name': str_item.name,
            'position_37': '1:12345',
            'position_38': '1:12345',
            'repeated_sequence': 'ATAT',
            'normal_range_0': 1,
            'normal_range_1': 2,
            'prepathogenic_range_0': 1,
            'prepathogenic_range_1': 2,
            'pathogenic_range_0': 1,
            'pathogenic_range_1': 2,
            "gene": str_item.gene_core.pk,
            "gene_name": "Gene name",
            "source": set([source, new_evidence]),
            "tags": [TagFactory().pk, ] + [tag.name for tag in str_item.tags.all()],
            "publications": ";".join([publication, fake.sentence()]),
            "phenotypes": ";".join([phenotype, fake.sentence(), fake.sentence()]),
            "moi": [x for x in Evaluation.MODES_OF_INHERITANCE][randint(1, 12)],
            "penetrance": GenePanelEntrySnapshot.PENETRANCE.Incomplete,
        }
        res = self.client.post(url, str_data)
        assert res.status_code == 302
        new_str = GenePanel.objects.get(pk=str_item.panel.panel.pk).active_panel.get_str(str_item.name)
        assert str_item.panel.panel.active_panel.version != str_item.panel.version
        new_current_number = new_str.panel.panel.active_panel.number_of_strs
        assert number_of_strs == new_current_number

    def test_edit_repeated_sequence(self):
        str_item = STRFactory()
        url = reverse_lazy('panels:edit_entity', kwargs={
            'pk': str_item.panel.panel.pk,
            'entity_type': 'str',
            'entity_name': str_item.name
        })

        number_of_strs = str_item.panel.number_of_strs

        # make sure new data has at least 1 of the same items
        source = str_item.evidence.last().name

        publication = str_item.publications[0]
        phenotype = str_item.publications[1]

        new_evidence = Evidence.ALL_SOURCES[randint(0, 9)]
        original_evidences = set([ev.name for ev in str_item.evidence.all()])
        original_evidences.add(new_evidence)

        str_data = {
            'name': str_item.name,
            'position_37': '1:12345',
            'position_38': '1:12345',
            'repeated_sequence': 'ATATAT',
            'normal_range_0': 1,
            'normal_range_1': 2,
            'prepathogenic_range_0': 1,
            'prepathogenic_range_1': 2,
            'pathogenic_range_0': 1,
            'pathogenic_range_1': 2,
            "gene": str_item.gene_core.pk,
            "gene_name": "Gene name",
            "source": set([source, new_evidence]),
            "tags": [TagFactory().pk, ] + [tag.name for tag in str_item.tags.all()],
            "publications": ";".join([publication, fake.sentence()]),
            "phenotypes": ";".join([phenotype, fake.sentence(), fake.sentence()]),
            "moi": [x for x in Evaluation.MODES_OF_INHERITANCE][randint(1, 12)],
            "penetrance": GenePanelEntrySnapshot.PENETRANCE.Incomplete,
        }
        res = self.client.post(url, str_data)
        assert res.status_code == 302
        new_str = GenePanel.objects.get(pk=str_item.panel.panel.pk).active_panel.get_str(str_item.name)
        assert new_str.repeated_sequence == 'ATATAT'

    def test_remove_gene_from_str(self):
        """We need ability to remove genes from STRs"""

        str_item = STRFactory()
        url = reverse_lazy('panels:edit_entity', kwargs={
            'pk': str_item.panel.panel.pk,
            'entity_type': 'str',
            'entity_name': str_item.name
        })

        number_of_strs = str_item.panel.number_of_strs

        # make sure new data has at least 1 of the same items
        source = str_item.evidence.last().name

        publication = str_item.publications[0]
        phenotype = str_item.publications[1]

        new_evidence = Evidence.ALL_SOURCES[randint(0, 9)]
        original_evidences = set([ev.name for ev in str_item.evidence.all()])
        original_evidences.add(new_evidence)

        str_data = {
            'name': str_item.name,
            'position_37': '1:12345',
            'position_38': '1:12345',
            'repeated_sequence': 'ATAT',
            'normal_range_0': 1,
            'normal_range_1': 2,
            'prepathogenic_range_0': 1,
            'prepathogenic_range_1': 2,
            'pathogenic_range_0': 1,
            'pathogenic_range_1': 2,
            "gene_name": "Gene name",
            "source": set([source, new_evidence]),
            "tags": [TagFactory().pk, ] + [tag.name for tag in str_item.tags.all()],
            "publications": ";".join([publication, fake.sentence()]),
            "phenotypes": ";".join([phenotype, fake.sentence(), fake.sentence()]),
            "moi": [x for x in Evaluation.MODES_OF_INHERITANCE][randint(1, 12)],
            "penetrance": GenePanelEntrySnapshot.PENETRANCE.Incomplete,
        }
        res = self.client.post(url, str_data)
        assert res.status_code == 302
        new_str = GenePanel.objects.get(pk=str_item.panel.panel.pk).active_panel.get_str(str_item.name)
        assert not new_str.gene_core
        assert not new_str.gene
        assert str_item.panel.panel.active_panel.version != str_item.panel.version
        new_current_number = new_str.panel.panel.active_panel.number_of_strs
        assert number_of_strs == new_current_number

    def test_remove_sources(self):
        """Remove sources via edit gene detail section"""

        str_item = STRFactory(
            penetrance=GenePanelEntrySnapshot.PENETRANCE.Incomplete
        )
        url = reverse_lazy('panels:edit_entity', kwargs={
            'pk': str_item.panel.panel.pk,
            'entity_type': 'str',
            'entity_name': str_item.name
        })

        str_data = {
            'name': str_item.name,
            'position_37': '1:12345',
            'position_38': '1:12345',
            'repeated_sequence': 'ATAT',
            'normal_range_0': 1,
            'normal_range_1': 2,
            'prepathogenic_range_0': 1,
            'prepathogenic_range_1': 2,
            'pathogenic_range_0': 1,
            'pathogenic_range_1': 2,
            "gene": str_item.gene_core.pk,
            "gene_name": "Gene name",
            "source": set([ev.name for ev in str_item.evidence.all()[1:]]),
            "tags": [tag.name for tag in str_item.tags.all()],
            "publications": ";".join([publication for publication in str_item.publications]),
            "phenotypes": ";".join([phenotype for phenotype in str_item.phenotypes]),
            "moi": str_item.moi,
            "penetrance": GenePanelEntrySnapshot.PENETRANCE.Complete,
        }
        res = self.client.post(url, str_data)
        assert res.status_code == 302
        new_str = GenePanel.objects.get(pk=str_item.panel.panel.pk).active_panel.get_str(str_item.name)
        assert new_str.penetrance != str_item.penetrance

    def test_add_tag_via_edit_details(self):
        """Set tags via edit gene detail section"""

        str_item = STRFactory(
            penetrance=GenePanelEntrySnapshot.PENETRANCE.Incomplete
        )
        url = reverse_lazy('panels:edit_entity', kwargs={
            'pk': str_item.panel.panel.pk,
            'entity_type': 'str',
            'entity_name': str_item.name
        })

        tag = TagFactory(name='some tag')

        str_data = {
            'name': str_item.name,
            'position_37': '1:12345',
            'position_38': '1:12345',
            'repeated_sequence': 'ATAT',
            'normal_range_0': 1,
            'normal_range_1': 2,
            'prepathogenic_range_0': 1,
            'prepathogenic_range_1': 2,
            'pathogenic_range_0': 1,
            'pathogenic_range_1': 2,
            "gene": str_item.gene_core.pk,
            "gene_name": "Gene name",
            "source": set([ev.name for ev in str_item.evidence.all()]),
            "tags": [tag.pk for tag in str_item.tags.all()] + [tag.pk, ],
            "publications": ";".join([publication for publication in str_item.publications]),
            "phenotypes": ";".join([phenotype for phenotype in str_item.phenotypes]),
            "moi": str_item.moi,
            "penetrance": GenePanelEntrySnapshot.PENETRANCE.Complete,
        }
        res = self.client.post(url, str_data)
        assert res.status_code == 302
        new_str = GenePanel.objects.get(pk=str_item.panel.panel.pk).active_panel.get_str(str_item.name)
        assert sorted(list(new_str.tags.all())) != sorted(list(str_item.tags.all()))

    def test_remove_tag_via_edit_details(self):
        """Remove tags via edit gene detail section"""

        str_item = STRFactory(
            penetrance=GenePanelEntrySnapshot.PENETRANCE.Incomplete
        )

        tag = TagFactory(name='some tag')
        str_item.tags.add(tag)

        url = reverse_lazy('panels:edit_entity', kwargs={
            'pk': str_item.panel.panel.pk,
            'entity_type': 'str',
            'entity_name': str_item.name
        })

        str_data = {
            'name': str_item.name,
            'position_37': '1:12345',
            'position_38': '1:12345',
            'repeated_sequence': 'ATAT',
            'normal_range_0': '1',
            'normal_range_1': '2',
            'prepathogenic_range_0': '1',
            'prepathogenic_range_1': '2',
            'pathogenic_range_0': '1',
            'pathogenic_range_1': '2',
            "gene": str_item.gene_core.pk,
            "gene_name": "Gene name",
            "source": set([ev.name for ev in str_item.evidence.all()]),
            "tags": [],
            "publications": ";".join([publication for publication in str_item.publications]),
            "phenotypes": ";".join([phenotype for phenotype in str_item.phenotypes]),
            "moi": str_item.moi,
            "penetrance": GenePanelEntrySnapshot.PENETRANCE.Complete,
        }
        res = self.client.post(url, str_data)
        assert res.status_code == 302
        new_str = GenePanel.objects.get(pk=str_item.panel.panel.pk).active_panel.get_str(str_item.name)
        assert list(new_str.tags.all()) == []

    def test_change_penetrance(self):
        """Test if a curator can change Gene penetrance"""

        str_item = STRFactory(
            penetrance=GenePanelEntrySnapshot.PENETRANCE.Incomplete
        )
        url = reverse_lazy('panels:edit_entity', kwargs={
            'pk': str_item.panel.panel.pk,
            'entity_type': 'str',
            'entity_name': str_item.name
        })

        str_data = {
            'name': str_item.name,
            'position_37': '1:12345',
            'position_38': '1:12345',
            'repeated_sequence': 'ATAT',
            'normal_range_0': 1,
            'normal_range_1': 2,
            'prepathogenic_range_0': 1,
            'prepathogenic_range_1': 2,
            'pathogenic_range_0': 1,
            'pathogenic_range_1': 2,
            "gene": str_item.gene_core.pk,
            "gene_name": "Gene name",
            "source": set([ev.name for ev in str_item.evidence.all()]),
            "tags": [tag.name for tag in str_item.tags.all()],
            "publications": ";".join([publication for publication in str_item.publications]),
            "phenotypes": ";".join([phenotype for phenotype in str_item.phenotypes]),
            "moi": str_item.moi,
            "penetrance": GenePanelEntrySnapshot.PENETRANCE.Complete,
        }
        res = self.client.post(url, str_data)
        assert res.status_code == 302
        new_str = GenePanel.objects.get(pk=str_item.panel.panel.pk).active_panel.get_str(str_item.name)
        assert new_str.penetrance != str_item.penetrance

    def test_add_publication(self):
        """Add a publication to a gene panel entry"""

        str_item = STRFactory(
            penetrance=GenePanelEntrySnapshot.PENETRANCE.Incomplete
        )
        str_item.publications = []
        str_item.save()

        url = reverse_lazy('panels:edit_entity', kwargs={
            'pk': str_item.panel.panel.pk,
            'entity_type': 'str',
            'entity_name': str_item.name
        })

        str_data = {
            'name': str_item.name,
            'position_37': '1:12345',
            'position_38': '1:12345',
            'repeated_sequence': 'ATAT',
            'normal_range_0': 1,
            'normal_range_1': 2,
            'prepathogenic_range_0': 1,
            'prepathogenic_range_1': 2,
            'pathogenic_range_0': 1,
            'pathogenic_range_1': 2,
            "gene": str_item.gene_core.pk,
            "gene_name": "Gene name",
            "source": set([ev.name for ev in str_item.evidence.all()]),
            "tags": [tag.name for tag in str_item.tags.all()],
            "publications": ";".join([fake.sentence(), fake.sentence()]),
            "phenotypes": ";".join([phenotype for phenotype in str_item.phenotypes]),
            "moi": str_item.moi,
            "penetrance": GenePanelEntrySnapshot.PENETRANCE.Complete,
        }
        res = self.client.post(url, str_data)
        assert res.status_code == 302
        new_str = GenePanel.objects.get(pk=str_item.panel.panel.pk).active_panel.get_str(str_item.name)
        assert new_str.publications != str_item.publications

    def test_remove_publication(self):
        """Remove a publication to a gene panel entry"""

        str_item = STRFactory(
            penetrance=GenePanelEntrySnapshot.PENETRANCE.Incomplete
        )
        str_item.publications = [fake.sentence(), fake.sentence()]
        str_item.save()

        url = reverse_lazy('panels:edit_entity', kwargs={
            'pk': str_item.panel.panel.pk,
            'entity_type': 'str',
            'entity_name': str_item.name
        })

        str_data = {
            'name': str_item.name,
            'position_37': '1:12345',
            'position_38': '1:12345',
            'repeated_sequence': 'ATAT',
            'normal_range_0': 1,
            'normal_range_1': 2,
            'prepathogenic_range_0': 1,
            'prepathogenic_range_1': 2,
            'pathogenic_range_0': 1,
            'pathogenic_range_1': 2,
            "gene": str_item.gene_core.pk,
            "gene_name": "Gene name",
            "source": set([ev.name for ev in str_item.evidence.all()]),
            "tags": [tag.name for tag in str_item.tags.all()],
            "publications": ";".join(str_item.publications[:1]),
            "phenotypes": ";".join([phenotype for phenotype in str_item.phenotypes]),
            "moi": str_item.moi,
            "penetrance": GenePanelEntrySnapshot.PENETRANCE.Complete,
        }
        res = self.client.post(url, str_data)
        assert res.status_code == 302
        new_str = GenePanel.objects.get(pk=str_item.panel.panel.pk).active_panel.get_str(str_item.name)
        assert new_str.publications == str_item.publications[:1]

    def test_edit_str_name_unit(self):
        str_item = STRFactory()
        old_str_name = str_item.name

        ap = GenePanel.objects.get(pk=str_item.panel.panel.pk).active_panel

        assert ap.has_str(old_str_name) is True
        new_data = {
            "name": 'NewSTR'
        }
        ap.update_str(self.verified_user, old_str_name, new_data)

        new_ap = GenePanel.objects.get(pk=str_item.panel.panel.pk).active_panel
        assert new_ap.has_str(old_str_name) is False
        assert new_ap.has_str('NewSTR') is True

    def test_update_str_preserves_comments_order(self):
        str_item = STRFactory()
        comments = list(CommentFactory.create_batch(4, user=self.verified_user))

        for ev in str_item.evaluation.all():
            ev.comments.add(comments.pop())

        max_comments_num = max([e.comments.count() for e in str_item.evaluation.all()])
        self.assertEqual(1, max_comments_num)

        old_str_name = str_item.name
        ap = GenePanel.objects.get(pk=str_item.panel.panel.pk).active_panel

        new_data = {
            "name": 'NewSTR'
        }
        ap.update_str(self.verified_user, old_str_name, new_data)

        new_ap = GenePanel.objects.get(pk=str_item.panel.panel.pk).active_panel
        new_str = new_ap.get_str('NewSTR')

        max_comments_num_after_update = max([e.comments.count() for e in new_str.evaluation.all()])
        self.assertEqual(1, max_comments_num_after_update)

    def test_edit_str_name_ajax(self):
        str_item = STRFactory()
        url = reverse_lazy('panels:edit_entity', kwargs={
            'pk': str_item.panel.panel.pk,
            'entity_type': 'str',
            'entity_name': str_item.name
        })

        old_str_name = str_item.name

        # make sure new data has at least 1 of the same items
        source = str_item.evidence.last().name
        publication = str_item.publications[0]
        phenotype = str_item.publications[1]

        gene_data = {
            'name': 'NewSTR',
            'position_37': '1:12345',
            'position_38': '1:12345',
            'repeated_sequence': 'ATAT',
            'normal_range_0': 1,
            'normal_range_1': 2,
            'prepathogenic_range_0': 1,
            'prepathogenic_range_1': 2,
            'pathogenic_range_0': 1,
            'pathogenic_range_1': 2,
            "gene": str_item.gene_core.pk,
            "gene_name": "Other name",
            "source": set([source, Evidence.ALL_SOURCES[randint(0, 9)]]),
            "tags": [TagFactory().pk, ] + [tag.name for tag in str_item.tags.all()],
            "publications": ";".join([publication, fake.sentence()]),
            "phenotypes": ";".join([phenotype, fake.sentence(), fake.sentence()]),
            "moi": [x for x in Evaluation.MODES_OF_INHERITANCE][randint(1, 12)],
            "penetrance": GenePanelEntrySnapshot.PENETRANCE.Incomplete,
        }
        res = self.client.post(url, gene_data)
        assert res.status_code == 302

        new_gps = GenePanel.objects.get(pk=str_item.panel.panel.pk).active_panel
        old_gps = GenePanelSnapshot.objects.get(pk=str_item.panel.pk)

        # check panel has no previous gene
        assert new_gps.has_str(old_str_name) is False

        # test previous panel contains old gene
        assert old_gps.has_str(old_str_name) is True
