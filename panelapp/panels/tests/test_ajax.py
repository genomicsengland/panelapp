from django.urls import reverse_lazy
from accounts.tests.setup import LoginGELUser
from panels.tests.factories import GenePanelEntrySnapshotFactory
from panels.models import GenePanel
from panels.models import TrackRecord


class AjaxGenePanelEntrySnapshotTest(LoginGELUser):
    gpes = None

    def setUp(self):
        super().setUp()
        self.gpes = GenePanelEntrySnapshotFactory()

    def helper_clear(self, content_type, additional_kwargs=None):
        kwargs = {
            'pk': self.gpes.panel.panel.pk,
            'gene_symbol': self.gpes.gene.get('gene_symbol')
        }

        if additional_kwargs:
            kwargs.update(additional_kwargs)

        url = reverse_lazy('panels:{}'.format(content_type), kwargs=kwargs)
        res = self.client.get(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        assert res.json().get('status') == 200

        gps = GenePanel.objects.get(pk=self.gpes.panel.panel.pk).active_panel
        gene = gps.get_gene(self.gpes.gene.get('gene_symbol'))
        assert gps.version != self.gpes.panel.version
        return res, gene

    def test_clear_phenotypes(self):
        res, gene = self.helper_clear('clear_gene_phenotypes')
        assert gene.phenotypes == []

    def test_clear_gene_publications(self):
        res, gene = self.helper_clear('clear_gene_publications')
        assert gene.publications == []

    def test_clear_gene_mode_of_pathogenicity(self):
        res, gene = self.helper_clear('clear_gene_mode_of_pathogenicity')
        assert gene.mode_of_pathogenicity == ""

    def test_clear_sources(self):
        res, gene = self.helper_clear('clear_gene_sources')
        assert gene.evidence.count() == 0

        self.assertTrue(gene.track.filter(issue_type=TrackRecord.ISSUE_TYPES.ClearSources).count() > 0)

    def test_clear_single_source(self):
        evidence = self.gpes.evidence.all()[0]
        before_count = self.gpes.evidence.count()
        evidence_count = self.gpes.evidence.filter(name=evidence.name).count()
        res, gene = self.helper_clear('clear_gene_source', additional_kwargs={'source': evidence.name})
        assert gene.evidence.count() == before_count - evidence_count
        assert res.content.find(str.encode(evidence.name)) == -1


class AjaxGenePanelEntryTest(LoginGELUser):
    gpes = None

    def setUp(self):
        super().setUp()
        self.gpes = GenePanelEntrySnapshotFactory()
        self.gpes2 = GenePanelEntrySnapshotFactory()

    def helper_panel(self, action):
        kwargs = {
            'pk': self.gpes.panel.panel.pk
        }
        url = reverse_lazy('panels:{}'.format(action), kwargs=kwargs)
        res = self.client.get(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        assert res.json().get('status') == 200
        return res

    def test_delete_panel(self):
        pk = self.gpes.panel.panel.pk
        res = self.helper_panel('delete_panel')
        assert GenePanel.objects.filter(pk=pk).count() == 0
        assert res.content.find(str.encode(self.gpes2.panel.panel.name))

    def test_approve_panel(self):
        self.gpes.panel.panel.approved = False
        self.gpes.panel.panel.save()

        self.helper_panel('approve_panel')
        assert GenePanel.objects.get(pk=self.gpes.panel.panel.pk).approved is True

    def test_reject_panel(self):
        self.gpes.panel.panel.approved = True
        self.gpes.panel.panel.save()

        self.helper_panel('reject_panel')
        assert GenePanel.objects.get(pk=self.gpes.panel.panel.pk).approved is False
