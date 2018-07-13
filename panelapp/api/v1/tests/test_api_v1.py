from django.test import TransactionTestCase
from django.urls import reverse_lazy
from accounts.tests.setup import LoginExternalUser
from panels.models import GenePanel
from panels.models import GenePanelSnapshot
from panels.tests.factories import GenePanelSnapshotFactory
from panels.tests.factories import GenePanelEntrySnapshotFactory
from panels.tests.factories import STRFactory


class TestAPIV1(LoginExternalUser):
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
        r = self.client.get(reverse_lazy('api:v1:panels-list'))
        self.assertEqual(r.status_code, 200)

    def test_list_panels_name(self):
        url = reverse_lazy('api:v1:panels-list')
        r = self.client.get(url)
        self.assertEqual(len(r.json()['results']), 3)
        self.assertEqual(r.status_code, 200)

    def test_retired_panels(self):
        url = reverse_lazy('api:v1:panels-list')

        self.gps.panel.status = GenePanel.STATUS.deleted
        self.gps.panel.save()

        r = self.client.get(url)
        self.assertEqual(len(r.json()['results']), 2)
        self.assertEqual(r.status_code, 200)

        # Test deleted panels
        url = reverse_lazy('api:v1:panels-list')
        r = self.client.get("{}?retired=True".format(url))
        self.assertEqual(len(r.json()['results']), 3)  # one for gpes via factory, 2nd - retired
        self.assertEqual(r.status_code, 200)

        # Test for unapproved panels
        self.gps_public.panel.status = GenePanel.STATUS.internal
        self.gps_public.panel.save()

        url = reverse_lazy('api:v1:panels-list')
        r = self.client.get("{}?retired=True".format(url))
        self.assertEqual(len(r.json()['results']), 2)  # only retired panel will be visible
        self.assertEqual(r.status_code, 200)

    def test_internal_panel(self):
        self.gps.panel.status = GenePanel.STATUS.internal
        self.gps.panel.save()
        url = reverse_lazy('api:v1:panels-detail', args=(self.gps.panel.pk, ))
        r = self.client.get(url)
        self.assertEqual(r.status_code, 404)
        self.assertEqual(r.json(), {'detail': 'Not found.'})

        self.gps.increment_version()
        self.gps.increment_version()
        r = self.client.get("{}?version=0.1".format(url))
        self.assertEqual(r.status_code, 200)

    def test_get_panel_name(self):
        r = self.client.get(reverse_lazy('api:v1:panels-detail', args=(self.gpes.panel.panel.name,)))
        self.assertEqual(r.status_code, 200)

    def test_get_panel_name_deleted(self):
        r = self.client.get(reverse_lazy('api:v1:panels-detail', args=(self.gpes_deleted.panel.panel.name,)))
        self.assertEqual(r.status_code, 404)
        self.assertEqual(r.json(), {'detail': 'Not found.'})

    def test_get_panel_internal(self):
        r = self.client.get(reverse_lazy('api:v1:panels-detail', args=(self.gpes_internal.panel.panel.name,)))
        self.assertEqual(r.status_code, 404)
        self.assertEqual(r.json(), {'detail': 'Not found.'})

    def test_get_panel_retired(self):
        r = self.client.get(reverse_lazy('api:v1:panels-detail', args=(self.gpes_retired.panel.panel.name,)))
        self.assertEqual(r.status_code, 404)
        self.assertEqual(r.json(), {'detail': 'Not found.'})

    def test_get_panel_pk(self):
        r = self.client.get(reverse_lazy('api:v1:panels-detail', args=(self.gpes.panel.panel.pk,)))
        self.assertEqual(r.status_code, 200)

    def test_get_panel_version(self):
        self.gpes.panel.increment_version()
        self.gpes.panel.increment_version()

        url = reverse_lazy('api:v1:panels-detail', args=(self.gpes.panel.panel.pk,))
        r = self.client.get("{}?version=0.1".format(url))
        self.assertEqual(r.status_code, 200)

        self.gps.panel.status = GenePanel.STATUS.retired
        self.gps.panel.save()

        url = reverse_lazy('api:v1:panels-detail', args=(self.gpes.panel.panel.pk,))
        r = self.client.get("{}?version=0.1".format(url))
        self.assertEqual(r.status_code, 200)
        self.assertTrue(b'Query Error' not in r.content)

    def test_panel_created_timestamp(self):
        self.gpes.panel.increment_version()
        url = reverse_lazy('api:v1:panels-list')
        res = self.client.get(url)
        # find gps panel
        title = self.gps_public.level4title.name
        current_time = str(self.gps_public.created).replace('+00:00', 'Z').replace(' ', 'T')
        gps_panel = [r for r in res.json()['results'] if r['name'] == title][0]
        self.assertEqual(gps_panel['version_created'], current_time)

        r = self.client.get(reverse_lazy('api:v1:panels-detail', args=(gps_panel['id'],))).json()
        self.assertEqual(r['version_created'], current_time)

    def test_get_search_gene(self):
        url = reverse_lazy('api:v1:genes-detail', args=(self.gpes.gene_core.gene_symbol,))
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)

    def test_search_by_gene(self):
        url = reverse_lazy('api:v1:genes-detail', args=(self.gpes.gene_core.gene_symbol,))
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)

        r = self.client.get("{}?panel_name={}".format(url, self.gps_public.level4title.name))
        self.assertEqual(r.status_code, 200)

        multi_genes_arg = "{},{}".format(self.genes[0].gene_core.gene_symbol, self.genes[1].gene_core.gene_symbol)
        multi_genes_url = reverse_lazy('api:v1:genes-detail', args=(multi_genes_arg,))
        r = self.client.get(multi_genes_url)
        self.assertEqual(r.status_code, 200)

    def test_strs_in_panel(self):
        r = self.client.get(reverse_lazy('api:v1:panels-detail', args=(self.str.panel.panel.pk,)))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['strs'][0]['entity_name'], self.str.name)
        self.assertEqual(r.json()['strs'][0]['grch37_coordinates'],
                         [self.str.position_37.lower, self.str.position_37.upper])
        self.assertEqual(r.json()['strs'][0]['grch38_coordinates'],
                         [self.str.position_38.lower, self.str.position_38.upper])
        self.assertEqual(r.json()['strs'][0]['pathogenic_repeats'], self.str.pathogenic_repeats)

    def test_super_panel(self):
        super_panel = GenePanelSnapshotFactory(panel__status=GenePanel.STATUS.public)
        super_panel.child_panels.set([self.gps_public, ])

        r_direct = self.client.get(reverse_lazy('api:v1:panels-detail', args=(self.gps_public.panel.pk,)))
        result_genes = list(sorted(r_direct.json()['genes'], key=lambda x: x.get('gene_symbol')))

        r = self.client.get(reverse_lazy('api:v1:panels-detail', args=(super_panel.panel.pk,)))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(result_genes, list(sorted(r.json()['genes'], key=lambda x: x.get('gene_symbol'))))
