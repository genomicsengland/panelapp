from django.test import TransactionTestCase
from django.urls import reverse_lazy
from panels.tests.factories import GenePanelSnapshotFactory
from panels.tests.factories import GenePanelEntrySnapshotFactory
from webservices.utils import make_null
from webservices.utils import convert_moi
from webservices.utils import convert_gel_status


class TestWebservices(TransactionTestCase):
    def setUp(self):
        super().setUp()
        self.gps = GenePanelSnapshotFactory(panel__approved=True)
        self.gpes = GenePanelEntrySnapshotFactory(panel=self.gps, penetrance="unknown")
        self.genes = GenePanelEntrySnapshotFactory.create_batch(4, panel=self.gps)

    def test_list_panels(self):
        r = self.client.get(reverse_lazy('webservices:list_panels'))
        list_panels_json = {
            'result': [
                {
                    'DiseaseGroup': self.gps.level4title.level2title,
                    'Name': self.gps.panel.name,
                    'DiseaseSubGroup': self.gps.level4title.level3title,
                    'Number_of_Genes': len(self.gps.get_all_entries),
                    'CurrentVersion': '0.0',
                    'Panel_Id': str(self.gps.panel_id),
                    'Relevant_disorders': self.gps.old_panels
                }
            ]
        }
        self.assertEqual(r.json(), list_panels_json)
        self.assertEqual(r.status_code, 200)

    def test_list_panels_name(self):
        url = reverse_lazy('webservices:list_panels')

        url = reverse_lazy('webservices:list_panels')
        r = self.client.get(url)
        self.assertEqual(len(r.json()['result']), 1)
        self.assertEqual(r.status_code, 200)

    def test_retired_panels(self):
        url = reverse_lazy('webservices:list_panels')

        self.gps.panel.deleted = True
        self.gps.panel.save()

        r = self.client.get(url)
        self.assertEqual(len(r.json()['result']), 0)
        self.assertEqual(r.status_code, 200)

        # Test deleted panels
        url = reverse_lazy('webservices:list_panels')
        r = self.client.get("{}?Retired=True".format(url))
        self.assertEqual(len(r.json()['result']), 2)  # one for gpes via factory, second for gps
        self.assertEqual(r.status_code, 200)

        # Test for unapproved panels
        self.gps.panel.approved = False
        self.gps.panel.save()
        url = reverse_lazy('webservices:list_panels')
        r = self.client.get("{}?Retired=True".format(url))
        self.assertEqual(len(r.json()['result']), 2)  # one for gpes via factory, second for gps
        self.assertEqual(r.status_code, 200)

    def panel_json(self, version='0.0'):
        genes = []
        for gene in self.gps.get_all_entries:
            genes.append({
                'Phenotypes': make_null(gene.phenotypes),
                'GeneSymbol': gene.gene.get('gene_symbol'),
                'EnsembleGeneIds': [],
                'ModeOfInheritance': make_null(convert_moi(gene.moi)),
                'Penetrance': make_null(gene.penetrance),
                'Publications': make_null(gene.publications),
                'Evidences': [ev.name for ev in gene.evidence.all()],
                'ModeOfPathogenicity': make_null(gene.mode_of_pathogenicity),
                'LevelOfConfidence': convert_gel_status(gene.saved_gel_status)
            })
        genes = sorted(genes, key=lambda x: x['GeneSymbol'])
        return {
            'result': {
                'Genes': genes,
                'SpecificDiseaseName': self.gps.panel.name,
                'version': version,
                'DiseaseGroup': self.gps.level4title.level2title,
                'DiseaseSubGroup': self.gps.level4title.level3title
            },
        }

    def test_get_panel_name(self):
        r = self.client.get(reverse_lazy('webservices:get_panel', args=(self.gps.panel.name,)))
        sorted_json = r.json()
        sorted_genes = sorted_json['result']['Genes']
        sorted_genes = sorted(sorted_genes, key=lambda x: x['GeneSymbol'])
        sorted_json['result']['Genes'] = sorted_genes
        self.assertEqual(sorted_json, self.panel_json())
        self.assertEqual(r.status_code, 200)

    def test_get_panel_pk(self):
        r = self.client.get(reverse_lazy('webservices:get_panel', args=(self.gps.panel.pk,)))
        sorted_json = r.json()
        sorted_genes = sorted_json['result']['Genes']
        sorted_genes = sorted(sorted_genes, key=lambda x: x['GeneSymbol'])
        sorted_json['result']['Genes'] = sorted_genes
        self.assertEqual(sorted_json, self.panel_json())
        self.assertEqual(r.status_code, 200)

    def test_get_panel_version(self):
        self.gps.increment_version()
        self.gps.increment_version()

        url = reverse_lazy('webservices:get_panel', args=(self.gps.panel.pk,))
        r = self.client.get("{}?version=0.1".format(url))
        sorted_genes = sorted(r.json()['result']['Genes'], key=lambda x: x['GeneSymbol'])
        self.assertEqual(sorted_genes, self.panel_json(version='0.1')['result']['Genes'])
        self.assertEqual(r.status_code, 200)

        self.gps.panel.approved = False
        self.gps.panel.save()

        url = reverse_lazy('webservices:get_panel', args=(self.gpes.panel.panel.pk,))
        r = self.client.get("{}?version=0.1".format(url))
        self.assertEqual(r.status_code, 200)
        self.assertTrue(b'Query Error' not in r.content)

    def test_get_search_gene(self):
        url = reverse_lazy('webservices:search_genes', args=(self.gpes.gene_core.gene_symbol,))
        r = self.client.get(url)
        self.assertEqual(r.json()['meta']['numOfResults'], 1)
        self.assertEqual(r.status_code, 200)

    def test_search_by_gene(self):
        url = reverse_lazy('webservices:search_genes', args=(self.gpes.gene_core.gene_symbol,))
        r = self.client.get(url)
        self.assertEqual(r.json()['meta']['numOfResults'], 1)
        self.assertEqual(r.status_code, 200)

        r = self.client.get("{}?ModeOfInheritance={}".format(url, self.gpes.moi))
        self.assertEqual(r.json()['meta']['numOfResults'], 1)
        self.assertEqual(r.status_code, 200)

        r = self.client.get("{}?ModeOfPathogenicity={}".format(url, self.gpes.mode_of_pathogenicity))
        self.assertEqual(r.json()['meta']['numOfResults'], 1)
        self.assertEqual(r.status_code, 200)

        r = self.client.get("{}?LevelOfConfidence={}".format(url, convert_gel_status(self.gpes.saved_gel_status)))
        self.assertEqual(r.json()['meta']['numOfResults'], 1)
        self.assertEqual(r.status_code, 200)

        r = self.client.get("{}?Penetrance={}".format(url, self.gpes.penetrance))
        self.assertEqual(r.json()['meta']['numOfResults'], 1)
        self.assertEqual(r.status_code, 200)

        r = self.client.get("{}?Evidences={}".format(url, self.gpes.evidence.first().name))
        self.assertEqual(r.json()['meta']['numOfResults'], 1)
        self.assertEqual(r.status_code, 200)

        r = self.client.get("{}?panel_name={}".format(url, self.gps.panel.name))
        self.assertEqual(r.json()['meta']['numOfResults'], 1)
        self.assertEqual(r.status_code, 200)

        multi_genes_arg = "{},{}".format(self.genes[0].gene_core.gene_symbol, self.genes[1].gene_core.gene_symbol)
        multi_genes_url = reverse_lazy('webservices:search_genes', args=(multi_genes_arg,))
        r = self.client.get(multi_genes_url)
        self.assertEqual(r.json()['meta']['numOfResults'], 2)
        self.assertEqual(r.status_code, 200)
