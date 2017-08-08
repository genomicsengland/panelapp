import json
import os
from datetime import datetime
from datetime import date
from django.urls import reverse_lazy
from faker import Factory
from accounts.tests.setup import LoginGELUser
from panels.models.import_tools import update_gene_collection
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

        file_path = os.path.join(os.path.dirname(__file__), 'test_import.json')
        test_gene_file = os.path.abspath(file_path)

        # Create genes to update
        update_symbol = []
        update = []
        with open(test_gene_file) as f:
            results = json.load(f)
            for r in results['update']:
                update.append(GeneFactory(gene_symbol=r['gene_symbol']).gene_symbol)
            for r in results['update_symbol']:
                update_symbol.append(GeneFactory(gene_symbol=r[1]).gene_symbol)

        with open(test_gene_file) as f:
            url = reverse_lazy('panels:upload_genes')
            self.client.post(url, {'gene_list': f})

        for us in update_symbol:
            self.assertFalse(Gene.objects.get(gene_symbol=us).active)
        for u in update:
            gene = Gene.objects.get(gene_symbol=u)
            if gene.ensembl_genes:
                self.assertTrue(gene.active)
            else:
                self.assertFalse(gene.active)


    def test_gene_from_json(self):
        gene_dict_file = os.path.join(os.path.dirname(__file__), 'gene_dict.json')
        with open(gene_dict_file) as f:
            dictionary = json.load(f)
            g = Gene.from_dict(dictionary=dictionary)
            dictionary['hgnc_date_symbol_changed'] = date(2004, 10, 15)
            dictionary['hgnc_release'] = datetime(2017, 7, 21, 0, 0)
            self.assertEqual(dictionary, g.dict_tr())

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

    def test_update_gene_collection(self):
        gene_to_update = GeneFactory()
        gene_to_delete = GeneFactory()
        gene_to_update_symbol = GeneFactory()

        gps = GenePanelSnapshotFactory()
        GenePanelEntrySnapshotFactory.create_batch(2, panel=gps)  # random genes
        GenePanelEntrySnapshotFactory.create(gene_core=gene_to_update, panel=gps)

        gps = GenePanelSnapshotFactory()
        GenePanelEntrySnapshotFactory.create_batch(2, panel=gps)  # random genes
        GenePanelEntrySnapshotFactory.create(gene_core=gene_to_update_symbol, panel=gps)

        to_insert = [
            Gene(gene_symbol='A', ensembl_genes={'inserted': True}).dict_tr(),
            Gene(gene_symbol='B', ensembl_genes={'inserted': True}).dict_tr(),
            ]

        to_update = [
            Gene(gene_symbol=gene_to_update.gene_symbol, ensembl_genes={'updated': True}).dict_tr()
        ]

        to_update_symbol = [
            (Gene(gene_symbol='C', ensembl_genes={'updated': True}).dict_tr(), gene_to_update_symbol.gene_symbol)
        ]

        to_delete = [
            gene_to_delete.gene_symbol
        ]

        migration = {
            'insert': to_insert,
            'update': to_update,
            'delete': to_delete,
            'update_symbol': to_update_symbol
        }
        update_gene_collection(migration)
        self.assertTrue(GenePanelEntrySnapshot.objects.get_active().get(
            gene_core__gene_symbol=gene_to_update.gene_symbol).gene.get('ensembl_genes')['updated'])
        updated_not_updated = [gpes.gene['ensembl_genes'] for gpes in GenePanelEntrySnapshot.objects.filter(
            gene_core__gene_symbol=gene_to_update.gene_symbol)]
        self.assertNotEqual(updated_not_updated[0], updated_not_updated[1])
        self.assertFalse(GenePanelEntrySnapshot.objects.get(
            gene_core__gene_symbol=gene_to_update_symbol.gene_symbol).gene_core.active)
        self.assertFalse(Gene.objects.get(gene_symbol=gene_to_update_symbol.gene_symbol).active)
        self.assertFalse(Gene.objects.get(gene_symbol=gene_to_delete.gene_symbol).active)
        self.assertTrue(Gene.objects.get(gene_symbol='A').active)
        self.assertTrue(GenePanelEntrySnapshot.objects.get(
            gene_core__gene_symbol='C').gene.get('ensembl_genes')['updated'])



    def test_get_panels_for_a_gene(self):
        gene = GeneFactory()

        gps = GenePanelSnapshotFactory()
        GenePanelEntrySnapshotFactory.create_batch(2, panel=gps)  # random genes
        GenePanelEntrySnapshotFactory.create(gene_core=gene, panel=gps)

        gps = GenePanelSnapshotFactory()
        GenePanelEntrySnapshotFactory.create_batch(2, panel=gps)  # random genes
        GenePanelEntrySnapshotFactory.create(gene_core=gene, panel=gps)

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
