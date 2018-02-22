from django.test import TransactionTestCase
from django.urls import reverse_lazy
from panels.models import GenePanel
from panels.models import GenePanelSnapshot
from panels.tests.factories import GenePanelSnapshotFactory
from panels.tests.factories import GenePanelEntrySnapshotFactory
from panels.tests.factories import STRFactory


class TestWebservices(TransactionTestCase):
    def setUp(self):
        super().setUp()
        self.gps = GenePanelSnapshotFactory(panel__status=GenePanel.STATUS.public)
        self.gps_public = GenePanelSnapshotFactory(panel__status=GenePanel.STATUS.public)
        self.gpes = GenePanelEntrySnapshotFactory(panel=self.gps_public)
        self.gpes_internal = GenePanelEntrySnapshotFactory(panel__panel__status=GenePanel.STATUS.internal)
        self.gpes_retired = GenePanelEntrySnapshotFactory(panel__panel__status=GenePanel.STATUS.retired)
        self.gpes_deleted = GenePanelEntrySnapshotFactory(panel__panel__status=GenePanel.STATUS.deleted)
        self.genes = GenePanelEntrySnapshotFactory.create_batch(4, panel=self.gps)
        self.str = STRFactory(panel__panel__status=GenePanel.STATUS.public)

    def test_list_panels(self):
        r = self.client.get(reverse_lazy('webservices:list_panels'))
        self.assertEqual(r.status_code, 200)

    def test_list_panels_name(self):
        url = reverse_lazy('webservices:list_panels')
        r = self.client.get(url)
        self.assertEqual(len(r.json()['result']), 3)
        self.assertEqual(r.status_code, 200)

    def test_retired_panels(self):
        url = reverse_lazy('webservices:list_panels')

        self.str.panel.panel.delete()
        self.gps.panel.status = GenePanel.STATUS.deleted
        self.gps.panel.save()

        r = self.client.get(url)
        self.assertEqual(len(r.json()['result']), 1)
        self.assertEqual(r.status_code, 200)

        # Test deleted panels
        url = reverse_lazy('webservices:list_panels')
        r = self.client.get("{}?Retired=True".format(url))
        self.assertEqual(len(r.json()['result']), 2)  # one for gpes via factory, 2nd - retired
        self.assertEqual(r.status_code, 200)

        # Test for unapproved panels
        self.gps_public.panel.status = GenePanel.STATUS.internal
        self.gps_public.panel.save()

        url = reverse_lazy('webservices:list_panels')
        r = self.client.get("{}?Retired=True".format(url))
        self.assertEqual(len(r.json()['result']), 1)  # only retired panel will be visible
        self.assertEqual(r.status_code, 200)

    def test_internal_panel(self):
        self.gps.panel.status = GenePanel.STATUS.internal
        self.gps.panel.save()
        url = reverse_lazy('webservices:get_panel', args=(self.gps.panel.pk, ))
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), ["Query Error: {} not found.".format(self.gps.panel.pk)])

        self.gps.increment_version()
        self.gps.increment_version()
        r = self.client.get("{}?version=0.1".format(url))
        self.assertEqual(r.status_code, 200)
        self.assertIsNot(type(r.json()), list)
        self.assertIsNotNone(r.json().get('result'))

    def test_get_panel_name(self):
        r = self.client.get(reverse_lazy('webservices:get_panel', args=(self.gpes.panel.panel.name,)))
        self.assertEqual(r.status_code, 200)

    def test_get_panel_name_deleted(self):
        r = self.client.get(reverse_lazy('webservices:get_panel', args=(self.gpes_deleted.panel.panel.name,)))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), ["Query Error: {} not found.".format(self.gpes_deleted.panel.panel.name)])

    def test_get_panel_internal(self):
        r = self.client.get(reverse_lazy('webservices:get_panel', args=(self.gpes_internal.panel.panel.name,)))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), ["Query Error: {} not found.".format(self.gpes_internal.panel.panel.name)])

    def test_get_panel_retired(self):
        r = self.client.get(reverse_lazy('webservices:get_panel', args=(self.gpes_retired.panel.panel.name,)))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), ["Query Error: {} not found.".format(self.gpes_retired.panel.panel.name)])

    def test_get_panel_pk(self):
        r = self.client.get(reverse_lazy('webservices:get_panel', args=(self.gpes.panel.panel.pk,)))
        self.assertEqual(r.status_code, 200)

    def test_get_panel_version(self):
        self.gpes.panel.increment_version()
        self.gpes.panel.increment_version()

        url = reverse_lazy('webservices:get_panel', args=(self.gpes.panel.panel.pk,))
        r = self.client.get("{}?version=0.1".format(url))
        self.assertEqual(r.status_code, 200)

        self.gps.panel.status = GenePanel.STATUS.retired
        self.gps.panel.save()

        url = reverse_lazy('webservices:get_panel', args=(self.gpes.panel.panel.pk,))
        r = self.client.get("{}?version=0.1".format(url))
        self.assertEqual(r.status_code, 200)
        self.assertTrue(b'Query Error' not in r.content)

    def test_get_search_gene(self):
        url = reverse_lazy('webservices:search_genes', args=(self.gpes.gene_core.gene_symbol,))
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)

    def test_search_by_gene(self):
        url = reverse_lazy('webservices:search_genes', args=(self.gpes.gene_core.gene_symbol,))
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)

        r = self.client.get("{}?ModeOfInheritance={}".format(url, self.gpes.moi))
        self.assertEqual(r.status_code, 200)

        r = self.client.get("{}?ModeOfPathogenicity={}".format(url, self.gpes.mode_of_pathogenicity))
        self.assertEqual(r.status_code, 200)

        r = self.client.get("{}?LevelOfConfidence={}".format(url, self.gpes.saved_gel_status))
        self.assertEqual(r.status_code, 200)

        r = self.client.get("{}?Penetrance={}".format(url, self.gpes.penetrance))
        self.assertEqual(r.status_code, 200)

        r = self.client.get("{}?Evidences={}".format(url, self.gpes.evidence.first().name))
        self.assertEqual(r.status_code, 200)

        r = self.client.get("{}?panel_name={}".format(url, self.gps.panel.name))
        self.assertEqual(r.status_code, 200)

        multi_genes_arg = "{},{}".format(self.genes[0].gene_core.gene_symbol, self.genes[1].gene_core.gene_symbol)
        multi_genes_url = reverse_lazy('webservices:search_genes', args=(multi_genes_arg,))
        r = self.client.get(multi_genes_url)
        self.assertEqual(r.status_code, 200)

    def test_strs_in_panel(self):
        r = self.client.get(reverse_lazy('webservices:get_panel', args=(self.str.panel.panel.pk,)))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['result']['STRs'][0]['Name'], self.str.name)
        self.assertEqual(r.json()['result']['STRs'][0]['Position'], self.str.position)
        self.assertEqual(r.json()['result']['STRs'][0]['PathogenicRange'], self.str.pathogenic_range)
