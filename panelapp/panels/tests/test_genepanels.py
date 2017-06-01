import os
from django.test import TestCase
from django.test import Client
from django.urls import reverse_lazy
from faker import Factory
from accounts.tests.setup import LoginUser
from panels.models import Gene
from panels.models import GenePanel
from panels.models import GenePanelSnapshot

fake = Factory.create()


class GeneTest(LoginUser):
    def setUp(self):
        super().setUp()

    def test_import_gene(self):
        res = None

        file_path = os.path.join(os.path.dirname(__file__), 'test_gene.tsv')
        test_gene_file = os.path.abspath(file_path)
        with open(test_gene_file) as f:
            url = reverse_lazy('panels:upload_genes')
            res = self.client.post(url, {'gene_list': f})

        assert Gene.objects.count() == 1


class GenePanelTest(LoginUser):
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
        self.client.post(reverse_lazy('panels:create'), self.panel_data)
        gp = GenePanel.objects.last()

        url = reverse_lazy('panels:update', kwargs={'pk': gp.pk})
        data = self.create_panel_data()
        res = self.client.post(url, data)

        gp = GenePanel.objects.last()
        assert gp.active_panel.major_version == 0
        assert gp.active_panel.minor_version == 1
        assert gp.name == data['level4']
