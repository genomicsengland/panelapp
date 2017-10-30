from django.test import TestCase


class RedirectsTests(TestCase):
    def test_homepage(self):
        res = self.client.get('/crowdsourcing')
        self.assertEqual(res.status_code, 301)

    def test_panelapp_homepage(self):
        res = self.client.get('/crowdsourcing/PanelApp/')
        self.assertEqual(res.status_code, 301)

    def test_genes(self):
        res = self.client.get('/crowdsourcing/PanelApp/Genes')
        self.assertEqual(res.status_code, 301)

    def test_gene(self):
        res = self.client.get('/crowdsourcing/PanelApp/Genes/ABC')
        self.assertEqual(res.status_code, 301)

    def test_panels_list(self):
        res = self.client.get('/crowdsourcing/PanelApp/PanelBrowser')
        self.assertEqual(res.status_code, 301)

    def test_view_panel(self):
        res = self.client.get('/crowdsourcing/PanelApp/EditPanel/558aa423bb5a16630e15b63c')
        self.assertEqual(res.status_code, 301)

    def test_view_panel_gene(self):
        res = self.client.get('/crowdsourcing/PanelApp/GeneReview/558aa423bb5a16630e15b63c/NTRK1')
        self.assertEqual(res.status_code, 301)

    def test_webservices(self):
        res = self.client.get('/crowdsourcing/WebServices/list_panels')
        self.assertEqual(res.status_code, 301)
