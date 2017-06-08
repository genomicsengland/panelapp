from random import randint
from django.urls import reverse_lazy
from faker import Factory
from accounts.tests.setup import LoginGELUser
from panels.models import GenePanel
from panels.models import Evaluation
from .factories import GenePanelEntrySnapshotFactory


fake = Factory.create()


class EvaluationTest(LoginGELUser):
    def test_add_evaluation(self):
        gpes = GenePanelEntrySnapshotFactory()
        url = reverse_lazy('panels:review_gene', kwargs={
            'pk': gpes.panel.panel.pk,
            'gene_symbol': gpes.gene.get('gene_symbol')
        })

        gene_data = {
            "rating": Evaluation.RATINGS.AMBER,
            "current_diagnostic": True,
            "comments": fake.sentence(),
            "publications": ";".join([fake.sentence(), fake.sentence()]),
            "phenotypes": ";".join([fake.sentence(), fake.sentence(), fake.sentence()]),
            "moi": [x for x in Evaluation.MODES_OF_INHERITANCE][randint(1, 12)],
            "mode_of_pathogenicity": [x for x in Evaluation.MODES_OF_PHATHOGENICITY][randint(1, 2)],
        }
        res = self.client.post(url, gene_data)
        assert res.status_code == 302

    def test_add_evaluation_comments_only(self):
        gpes = GenePanelEntrySnapshotFactory()
        url = reverse_lazy('panels:review_gene', kwargs={
            'pk': gpes.panel.panel.pk,
            'gene_symbol': gpes.gene.get('gene_symbol')
        })

        gene_data = {
            "comments": fake.sentence(),
        }
        res = self.client.post(url, gene_data)
        assert res.status_code == 302

        assert gpes.evaluation.get(user=self.gel_user).comments.count() == 1

        gene_data = {
            "comments": fake.sentence(),
        }
        res = self.client.post(url, gene_data)
        gpes = GenePanel.objects.get(pk=gpes.panel.panel.pk).active_panel.get_gene(gpes.gene.get('gene_symbol'))
        assert gpes.evaluation.get(user=self.gel_user).comments.count() == 2

    def test_change_evaluation(self):
        gpes = GenePanelEntrySnapshotFactory()
        url = reverse_lazy('panels:review_gene', kwargs={
            'pk': gpes.panel.panel.pk,
            'gene_symbol': gpes.gene.get('gene_symbol')
        })

        old_phenotypes = [fake.sentence(), fake.sentence(), fake.sentence()]
        gene_data = {
            "rating": Evaluation.RATINGS.AMBER,
            "current_diagnostic": True,
            "comments": fake.sentence(),
            "publications": ";".join([fake.sentence(), fake.sentence()]),
            "phenotypes": ";".join(old_phenotypes),
            "moi": [x for x in Evaluation.MODES_OF_INHERITANCE][randint(1, 12)],
            "mode_of_pathogenicity": [x for x in Evaluation.MODES_OF_PHATHOGENICITY][randint(1, 2)],
        }
        self.client.post(url, gene_data)
        assert Evaluation.objects.filter(user=self.gel_user).count() == 1

        gene_data = {
            "moi": [x for x in Evaluation.MODES_OF_INHERITANCE][randint(1, 12)],
            "mode_of_pathogenicity": [x for x in Evaluation.MODES_OF_PHATHOGENICITY][randint(1, 2)],
        }
        self.client.post(url, gene_data)
        assert Evaluation.objects.filter(user=self.gel_user).count() == 1
        assert Evaluation.objects.get(user=self.gel_user).phenotypes == old_phenotypes


class GeneReadyTest(LoginGELUser):
    def test_mark_as_ready(self):
        gpes = GenePanelEntrySnapshotFactory()
        url = reverse_lazy('panels:mark_gene_as_ready', kwargs={
            'pk': gpes.panel.panel.pk,
            'gene_symbol': gpes.gene.get('gene_symbol')
        })

        res = self.client.post(url, {'comments': fake.sentence()})

        gene = GenePanel.objects.get(pk=gpes.panel.panel.pk).active_panel.get_gene(gpes.gene.get('gene_symbol'))
        assert gene.ready is True
