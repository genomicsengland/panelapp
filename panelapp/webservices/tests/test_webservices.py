from django.test import TransactionTestCase
from django.urls import reverse_lazy
from panels.models import GenePanel
from panels.models import GenePanelSnapshot
from panels.models import Evaluation
from panels.tests.factories import GenePanelSnapshotFactory
from panels.tests.factories import GenePanelEntrySnapshotFactory
from panels.tests.factories import STRFactory
from panels.tests.factories import RegionFactory
from webservices.utils import convert_mop


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
        self.region = RegionFactory(panel__panel__status=GenePanel.STATUS.public)

    def test_list_panels(self):
        r = self.client.get(reverse_lazy('webservices:list_panels'))
        self.assertEqual(r.status_code, 200)

    def test_list_panels_name(self):
        url = reverse_lazy('webservices:list_panels')
        r = self.client.get(url)
        self.assertEqual(len(r.json()['result']), 4)
        self.assertEqual(r.status_code, 200)

    def test_retired_panels(self):
        url = reverse_lazy('webservices:list_panels')

        self.gps.panel.status = GenePanel.STATUS.deleted
        self.gps.panel.save()

        r = self.client.get(url)
        self.assertEqual(len(r.json()['result']), 2)
        self.assertEqual(r.status_code, 200)

        # Test deleted panels
        url = reverse_lazy('webservices:list_panels')
        r = self.client.get("{}?Retired=True".format(url))
        self.assertEqual(len(r.json()['result']), 3)  # one for gpes via factory, 2nd - retired
        self.assertEqual(r.status_code, 200)

        # Test for unapproved panels
        self.gps_public.panel.status = GenePanel.STATUS.internal
        self.gps_public.panel.save()

        url = reverse_lazy('webservices:list_panels')
        r = self.client.get("{}?Retired=True".format(url))
        self.assertEqual(len(r.json()['result']), 2)  # only retired panel will be visible
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

    def test_panel_created_timestamp(self):
        self.gpes.panel.increment_version()
        url = reverse_lazy('webservices:list_panels')
        res = self.client.get(url)
        # find gps panel
        title = self.gps_public.panel.name
        current_time = str(self.gps_public.created).replace('+00:00', 'Z').replace(' ', 'T')
        gps_panel = [r for r in res.json()['result'] if r['Name'] == title][0]
        self.assertEqual(gps_panel['CurrentCreated'], current_time)

        r = self.client.get(reverse_lazy('webservices:get_panel', args=(self.gps_public.panel.name,))).json()
        self.assertEqual(r['result']['Created'], current_time)

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
        self.assertEqual(r.json()['result']['STRs'][0]['GRCh37Coordinates'],
                         [self.str.position_37.lower, self.str.position_37.upper])
        self.assertEqual(r.json()['result']['STRs'][0]['GRCh38Coordinates'],
                         [self.str.position_38.lower, self.str.position_38.upper])
        self.assertEqual(r.json()['result']['STRs'][0]['PathogenicRepeats'], self.str.pathogenic_repeats)

    def test_super_panel(self):
        super_panel = GenePanelSnapshotFactory(panel__status=GenePanel.STATUS.public)
        super_panel.child_panels.set([self.gps_public, ])

        r_direct = self.client.get(reverse_lazy('webservices:get_panel', args=(self.gps_public.panel.pk,)))
        result_genes = list(sorted(r_direct.json()['result']['Genes'], key=lambda x: x.get('GeneSymbol')))

        r = self.client.get(reverse_lazy('webservices:get_panel', args=(super_panel.panel.pk,)))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(result_genes, list(sorted(r.json()['result']['Genes'], key=lambda x: x.get('GeneSymbol'))))

    def test_no_loss_of_function(self):
        url = reverse_lazy('webservices:search_genes', args=(self.gpes.gene_core.gene_symbol,))
        r = self.client.get("{}?ModeOfPathogenicity={}".format(url, 'no_loss_of_function'))
        self.assertEqual(len(r.json()['results']), 0)

        self.gpes.mode_of_pathogenicity = convert_mop('no_loss_of_function', back=True)
        self.gpes.save()

        r = self.client.get("{}?ModeOfPathogenicity={}".format(url, 'no_loss_of_function'))
        self.assertEqual(len(r.json()['results']), 1)
        self.assertEqual(r.json()['results'][0]['GeneSymbol'], self.gpes.gene.get('gene_symbol'))

    def test_region_in_panel(self):
        r = self.client.get(reverse_lazy('webservices:get_panel', args=(self.region.panel.panel.pk,)))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['result']['Regions'][0]['Name'], self.region.name)
        self.assertEqual(r.json()['result']['Regions'][0]['GRCh37Coordinates'],
                         [self.region.position_37.lower, self.region.position_37.upper])
        self.assertEqual(r.json()['result']['Regions'][0]['GRCh38Coordinates'],
                         [self.region.position_38.lower, self.region.position_38.upper])
        self.assertEqual(sorted(r.json()['result']['Regions'][0]['ConsequenceSOTerms']), sorted(self.region.type_of_effect_impact))
