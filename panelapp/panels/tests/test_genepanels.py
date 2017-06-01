import os
from django.test import Client
from django.urls import reverse_lazy
from faker import Factory
from accounts.tests.setup import LoginGELUser
from panels.models import Gene
from panels.models import GenePanel
from panels.models import GenePanelSnapshot
from panels.models import GenePanelEntrySnapshot
from .factories import GeneFactory
from .factories import GenePanelSnapshotFactory
from .factories import GenePanelEntrySnapshotFactory


fake = Factory.create()


class GeneTest(LoginGELUser):
    def setUp(self):
        super().setUp()

    def test_import_gene(self):
        """
        Test Gene import. This also tests CellBaseConnector, which actually makes
        requests to the server. We can mock it later if necessary.
        """

        file_path = os.path.join(os.path.dirname(__file__), 'test_gene_data.tsv')
        test_gene_file = os.path.abspath(file_path)

        with open(test_gene_file) as f:
            url = reverse_lazy('panels:upload_genes')
            self.client.post(url, {'gene_list': f})

        assert Gene.objects.count() == 1


class GenePanelTest(LoginGELUser):
    def setUp(self):
        super().setUp()

        self.panel_data = self.create_panel_data()

    def create_panel_data(self):
        return {
            'level2': fake.sentence(nb_words=6, variable_nb_words=True),
            'level3': fake.sentence(nb_words=6, variable_nb_words=True),
            'level4': fake.sentence(nb_words=6, variable_nb_words=True),
            'description': fake.text(max_nb_chars=300),
            'omim': fake.sentences(nb=3),
            'orphanet': fake.sentences(nb=3),
            'hpo': fake.sentences(nb=3),
            'old_panels': fake.sentences(nb=3)
        }

    def test_create_unauthorised(self):
        c = Client()
        res = c.post(reverse_lazy('panels:create'), self.panel_data)
        assert res.status_code == 403

    def test_create_unauthorised_external_reviewer(self):
        c = Client()
        c.force_login(self.external_user)
        res = c.post(reverse_lazy('panels:create'), self.panel_data)
        assert res.status_code == 403

    def test_create_gel_reviewer(self):
        res = self.client.post(reverse_lazy('panels:create'), self.panel_data)
        assert res.status_code == 302

        gp = GenePanel.objects.get(name=self.panel_data['level4'])
        assert gp
        assert gp.active_panel.major_version == 0
        assert gp.active_panel.minor_version == 0

    def test_update_panel(self):
        gps = GenePanelSnapshotFactory()
        url = reverse_lazy('panels:update', kwargs={'pk': gps.panel.pk})
        data = self.create_panel_data()
        self.client.post(url, data)

        gp = GenePanel.objects.get(pk=gps.panel.pk)
        assert gp.active_panel.major_version == 0
        assert gp.active_panel.minor_version == 1
        assert gp.name == data['level4']

    def test_update_panel_many_to_many(self):
        gpes = GenePanelEntrySnapshotFactory()
        url = reverse_lazy('panels:update', kwargs={'pk': gpes.panel.panel.pk})
        data = self.create_panel_data()
        self.client.post(url, data)

        gp = GenePanel.objects.get(pk=gpes.panel.panel.pk)

        active_snapshot = gp.active_panel
        assert active_snapshot.major_version == 0
        assert active_snapshot.minor_version == 1
        assert gp.name == data['level4']
        assert active_snapshot.get_all_entries.count() == 1

    def test_mark_all_genes_not_ready(self):
        gps = GenePanelSnapshotFactory()
        GenePanelEntrySnapshotFactory.create_batch(5, ready=True, panel=gps)
        assert GenePanelEntrySnapshot.objects.filter(ready=True).count() == 5

        url = reverse_lazy('panels:mark_not_ready', kwargs={'pk': gps.panel.pk})
        res = self.client.get(url)
        assert GenePanelEntrySnapshot.objects.filter(ready=True).count() == 0
        assert res.status_code == 302

    def test_delete_gene(self):
        gps = GenePanelSnapshotFactory()
        genes = GenePanelEntrySnapshotFactory.create_batch(5, panel=gps)
        gene_symbol = genes[2].gene['gene_symbol']

        url = reverse_lazy('panels:delete_gene', kwargs={'pk': gps.panel.pk, 'gene_symbol': gene_symbol})
        res = self.client.get(url)

        new_gps = GenePanel.objects.get(pk=gps.panel.pk).active_panel

        assert new_gps.has_gene(gene_symbol) is False
        assert res.status_code == 302

    def test_active_panel(self):
        """
        Make sure GenePanel.active_panel returns correct panel
        """

        gps = GenePanelSnapshotFactory()
        gps2 = GenePanelSnapshotFactory()
        gps.increment_version()
        gps.increment_version()
        gps.increment_version()
        gps.increment_version()
        gps.increment_version()

        assert gps.minor_version == 5

        gp = GenePanel.objects.get(pk=gps.panel.pk)
        assert gp.active_panel == gps

        gps2.increment_version()
        gps2.increment_version()

        assert gps2.minor_version == 2
        gp2 = GenePanel.objects.get(pk=gps2.panel.pk)
        assert gp2.active_panel == gps2

    def test_get_panels_for_a_gene(self):
        gene = GeneFactory()

        gps = GenePanelSnapshotFactory()
        GenePanelEntrySnapshotFactory.create_batch(5, panel=gps)  # random genes
        GenePanelEntrySnapshotFactory.create(gene_core=gene, panel=gps)

        gps2 = GenePanelSnapshotFactory()
        GenePanelEntrySnapshotFactory.create_batch(5, panel=gps2)  # random genes
        GenePanelEntrySnapshotFactory.create(gene_core=gene, panel=gps2)

        gps3 = GenePanelSnapshotFactory()
        GenePanelEntrySnapshotFactory.create_batch(5, panel=gps3)  # random genes
        GenePanelEntrySnapshotFactory.create(gene_core=gene, panel=gps3)

        gps4 = GenePanelSnapshotFactory()
        GenePanelEntrySnapshotFactory.create_batch(5, panel=gps4)  # random genes

        assert GenePanelSnapshot.objects.get_gene_panels(gene.gene_symbol).count() == 3

        url = "{}?gene={}".format(reverse_lazy('panels:index'), gene.gene_symbol)
        self.client.get(url)
