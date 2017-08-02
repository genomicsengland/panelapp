import os
from django.urls import reverse_lazy
from faker import Factory
from accounts.tests.setup import LoginGELUser
from panels.models import Gene
from panels.models import GenePanelEntrySnapshot
from panels.utils import CellBaseConnector
from panels.tests.factories import GeneFactory
from panels.tests.factories import GenePanelSnapshotFactory
from panels.tests.factories import GenePanelEntrySnapshotFactory


fake = Factory.create()


class GeneTest(LoginGELUser):
    "Test gene import"

    def test_import_gene(self):
        """
        Test Gene import. This also tests CellBaseConnector, which actually makes
        requests to the server. We can mock it later if necessary.
        """

        file_path = os.path.join(os.path.dirname(__file__), 'import_gene_data.tsv')
        test_gene_file = os.path.abspath(file_path)

        with open(test_gene_file) as f:
            url = reverse_lazy('panels:upload_genes')
            self.client.post(url, {'gene_list': f})

        assert Gene.objects.count() == 1

    def test_download_genes(self):
        gps = GenePanelSnapshotFactory()
        GenePanelEntrySnapshotFactory.create_batch(2, panel=gps)

        res = self.client.get(reverse_lazy('panels:download_genes'))
        self.assertEqual(res.status_code, 200)

    def test_list_genes(self):
        GenePanelEntrySnapshotFactory.create_batch(3)
        r = self.client.get(reverse_lazy('panels:gene_list'))
        self.assertEqual(r.status_code, 200)

    def test_gene_not_ready(self):
        gpes = GenePanelEntrySnapshotFactory()
        url = reverse_lazy('panels:mark_gene_as_not_ready', args=(gpes.panel.panel.pk, gpes.gene.get('gene_symbol')))
        r = self.client.post(url, {})
        self.assertEqual(r.status_code, 302)

    def test_get_panels_for_a_gene(self):
        gene = GeneFactory()

        gps = GenePanelSnapshotFactory()
        GenePanelEntrySnapshotFactory.create_batch(2, panel=gps)  # random genes
        GenePanelEntrySnapshotFactory.create(gene_core=gene, panel=gps)

        gps2 = GenePanelSnapshotFactory()
        GenePanelEntrySnapshotFactory.create_batch(2, panel=gps2)  # random genes
        GenePanelEntrySnapshotFactory.create(gene_core=gene, panel=gps2)

        gps3 = GenePanelSnapshotFactory()
        GenePanelEntrySnapshotFactory.create_batch(2, panel=gps3)  # random genes
        GenePanelEntrySnapshotFactory.create(gene_core=gene, panel=gps3)

        gps4 = GenePanelSnapshotFactory()
        GenePanelEntrySnapshotFactory.create_batch(2, panel=gps4)  # random genes

        assert GenePanelEntrySnapshot.objects.get_gene_panels(gene.gene_symbol).count() == 3

        url = reverse_lazy('panels:gene_detail', kwargs={'slug': gene.gene_symbol})
        res = self.client.get(url)
        assert len(res.context_data['entries']) == 3

    def test_CBC(self):
        cbc = CellBaseConnector()
        assert cbc.get_transcripts(["B3GALT6"])
        assert cbc.get_exons(["B3GALT6"])
        assert cbc.get_gene(["B3GALT6"])
