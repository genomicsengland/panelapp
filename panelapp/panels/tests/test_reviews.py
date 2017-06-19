import os
from random import randint
from django.urls import reverse_lazy
from faker import Factory
from accounts.tests.setup import LoginGELUser
from panels.models import GenePanel
from panels.models import Evaluation
from panels.models import GenePanelEntrySnapshot
from .factories import TagFactory
from .factories import GeneFactory
from .factories import GenePanelFactory
from .factories import GenePanelSnapshotFactory
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
            "mode_of_pathogenicity": [x for x in Evaluation.MODES_OF_PATHOGENICITY][randint(1, 2)],
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
            "mode_of_pathogenicity": [x for x in Evaluation.MODES_OF_PATHOGENICITY][randint(1, 2)],
        }
        self.client.post(url, gene_data)
        assert Evaluation.objects.filter(user=self.gel_user).count() == 1

        gene_data = {
            "moi": [x for x in Evaluation.MODES_OF_INHERITANCE][randint(1, 12)],
            "mode_of_pathogenicity": [x for x in Evaluation.MODES_OF_PATHOGENICITY][randint(1, 2)],
        }
        self.client.post(url, gene_data)
        assert Evaluation.objects.filter(user=self.gel_user).count() == 1
        assert Evaluation.objects.get(user=self.gel_user).phenotypes == old_phenotypes


class GeneReviewTest(LoginGELUser):
    def test_mark_as_ready(self):
        gpes = GenePanelEntrySnapshotFactory()
        url = reverse_lazy('panels:mark_gene_as_ready', kwargs={
            'pk': gpes.panel.panel.pk,
            'gene_symbol': gpes.gene.get('gene_symbol')
        })

        self.client.post(url, {'ready_comment': fake.sentence()})
        gene = GenePanel.objects.get(pk=gpes.panel.panel.pk).active_panel.get_gene(gpes.gene.get('gene_symbol'))
        assert gene.ready is True

    def test_update_tags(self):
        gpes = GenePanelEntrySnapshotFactory()
        url = reverse_lazy('panels:update_gene_tags', kwargs={
            'pk': gpes.panel.panel.pk,
            'gene_symbol': gpes.gene.get('gene_symbol')
        })

        tag1 = TagFactory()
        tag2 = TagFactory()

        res = self.client.post(url, {'tags': [tag1.pk, tag2.pk]}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        gene = GenePanel.objects.get(pk=gpes.panel.panel.pk).active_panel.get_gene(gpes.gene.get('gene_symbol'))
        assert res.json().get('status') == 200
        assert gene.tags.count() == 2

    def test_update_mop(self):
        gpes = GenePanelEntrySnapshotFactory()
        url = reverse_lazy('panels:update_gene_mop', kwargs={
            'pk': gpes.panel.panel.pk,
            'gene_symbol': gpes.gene.get('gene_symbol')
        })

        mop = [x for x in Evaluation.MODES_OF_PATHOGENICITY][randint(1, 2)]
        data = {'comment': fake.sentence(), 'mode_of_pathogenicity': mop[1]}

        res = self.client.post(url, data, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        gene = GenePanel.objects.get(pk=gpes.panel.panel.pk).active_panel.get_gene(gpes.gene.get('gene_symbol'))
        assert res.json().get('status') == 200
        assert gene.comments.count() == 1
        assert gene.mode_of_pathogenicity == mop[1]

    def test_update_moi(self):
        gpes = GenePanelEntrySnapshotFactory()
        url = reverse_lazy('panels:update_gene_moi', kwargs={
            'pk': gpes.panel.panel.pk,
            'gene_symbol': gpes.gene.get('gene_symbol')
        })

        moi = [x for x in Evaluation.MODES_OF_INHERITANCE][randint(1, 2)]
        data = {'comment': fake.sentence(), 'moi': moi[1]}

        res = self.client.post(url, data, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        gene = GenePanel.objects.get(pk=gpes.panel.panel.pk).active_panel.get_gene(gpes.gene.get('gene_symbol'))
        assert res.json().get('status') == 200
        assert gene.comments.count() == 1
        assert gene.moi == moi[1]

    def test_update_phenotypes(self):
        gpes = GenePanelEntrySnapshotFactory()
        url = reverse_lazy('panels:update_gene_phenotypes', kwargs={
            'pk': gpes.panel.panel.pk,
            'gene_symbol': gpes.gene.get('gene_symbol')
        })

        phenotypes_array = [fake.word(), fake.word()]
        phenotypes = "{}; {}".format(phenotypes_array[0], phenotypes_array[1])
        data = {'comment': fake.sentence(), 'phenotypes': phenotypes}

        res = self.client.post(url, data, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        gene = GenePanel.objects.get(pk=gpes.panel.panel.pk).active_panel.get_gene(gpes.gene.get('gene_symbol'))
        assert res.json().get('status') == 200
        assert gene.comments.count() == 1
        assert gene.phenotypes == phenotypes_array

    def test_update_publications(self):
        gpes = GenePanelEntrySnapshotFactory()
        url = reverse_lazy('panels:update_gene_publications', kwargs={
            'pk': gpes.panel.panel.pk,
            'gene_symbol': gpes.gene.get('gene_symbol')
        })

        publications_array = [fake.word(), fake.word()]
        publications = "{}; {}".format(publications_array[0], publications_array[1])
        data = {'comment': fake.sentence(), 'publications': publications}

        res = self.client.post(url, data, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        gene = GenePanel.objects.get(pk=gpes.panel.panel.pk).active_panel.get_gene(gpes.gene.get('gene_symbol'))
        assert res.json().get('status') == 200
        assert gene.comments.count() == 1
        assert gene.publications == publications_array

    def test_update_rating(self):
        gpes = GenePanelEntrySnapshotFactory()
        url = reverse_lazy('panels:update_gene_rating', kwargs={
            'pk': gpes.panel.panel.pk,
            'gene_symbol': gpes.gene.get('gene_symbol')
        })

        new_status = 0
        data = {'comment': fake.sentence(), 'status': new_status}

        res = self.client.post(url, data, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        gene = GenePanel.objects.get(pk=gpes.panel.panel.pk).active_panel.get_gene(gpes.gene.get('gene_symbol'))
        assert res.json().get('status') == 200
        assert gene.comments.count() == 1
        assert gene.saved_gel_status == new_status

        new_status = 1
        data = {'comment': fake.sentence(), 'status': new_status}

        res = self.client.post(url, data, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        gene = GenePanel.objects.get(pk=gpes.panel.panel.pk).active_panel.get_gene(gpes.gene.get('gene_symbol'))
        assert res.json().get('status') == 200
        assert gene.comments.count() == 2
        assert gene.saved_gel_status == new_status

        new_status = 2
        data = {'comment': fake.sentence(), 'status': new_status}

        res = self.client.post(url, data, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        gene = GenePanel.objects.get(pk=gpes.panel.panel.pk).active_panel.get_gene(gpes.gene.get('gene_symbol'))
        assert res.json().get('status') == 200
        assert gene.comments.count() == 3
        assert gene.saved_gel_status == new_status

        new_status = 3
        data = {'comment': fake.sentence(), 'status': new_status}

        res = self.client.post(url, data, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        gene = GenePanel.objects.get(pk=gpes.panel.panel.pk).active_panel.get_gene(gpes.gene.get('gene_symbol'))
        assert res.json().get('status') == 200
        assert gene.comments.count() == 4
        assert gene.saved_gel_status == new_status

    def test_delete_evaluation(self):
        gpes = GenePanelEntrySnapshotFactory()

        evaluation_url = reverse_lazy('panels:review_gene', kwargs={
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
            "mode_of_pathogenicity": [x for x in Evaluation.MODES_OF_PATHOGENICITY][randint(1, 2)],
        }
        self.client.post(evaluation_url, gene_data, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        gene = GenePanel.objects.get(pk=gpes.panel.panel.pk).active_panel.get_gene(gpes.gene.get('gene_symbol'))
        assert gene.is_reviewd_by_user(self.gel_user) is True

        delete_evaluation_url = reverse_lazy('panels:delete_evaluation_by_user', kwargs={
            'pk': gpes.panel.panel.pk,
            'gene_symbol': gpes.gene.get('gene_symbol'),
            'evaluation_pk': gene.evaluation.get(user=self.gel_user).pk
        })
        res = self.client.get(delete_evaluation_url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        assert res.json().get('status') == 200
        assert gene.is_reviewd_by_user(self.gel_user) is False

    def test_delete_comment(self):
        gpes = GenePanelEntrySnapshotFactory()

        evaluation_url = reverse_lazy('panels:review_gene', kwargs={
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
            "mode_of_pathogenicity": [x for x in Evaluation.MODES_OF_PATHOGENICITY][randint(1, 2)],
        }
        self.client.post(evaluation_url, gene_data, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        gene = GenePanel.objects.get(pk=gpes.panel.panel.pk).active_panel.get_gene(gpes.gene.get('gene_symbol'))
        evaluation = gene.evaluation.get(user=self.gel_user)

        assert evaluation.comments.count() == 1

        delete_comment_url = reverse_lazy('panels:delete_comment_by_user', kwargs={
            'pk': gpes.panel.panel.pk,
            'gene_symbol': gpes.gene.get('gene_symbol'),
            'comment_pk': evaluation.comments.first().pk
        })
        res = self.client.get(delete_comment_url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        assert res.json().get('status') == 200
        assert evaluation.comments.count() == 0

    def test_edit_comment(self):
        gpes = GenePanelEntrySnapshotFactory()

        evaluation_url = reverse_lazy('panels:review_gene', kwargs={
            'pk': gpes.panel.panel.pk,
            'gene_symbol': gpes.gene.get('gene_symbol')
        })

        comment = fake.sentence()

        gene_data = {
            "rating": Evaluation.RATINGS.AMBER,
            "current_diagnostic": True,
            "comments": comment,
            "publications": ";".join([fake.sentence(), fake.sentence()]),
            "phenotypes": ";".join([fake.sentence(), fake.sentence(), fake.sentence()]),
            "moi": [x for x in Evaluation.MODES_OF_INHERITANCE][randint(1, 12)],
            "mode_of_pathogenicity": [x for x in Evaluation.MODES_OF_PATHOGENICITY][randint(1, 2)],
        }
        self.client.post(evaluation_url, gene_data, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        gene = GenePanel.objects.get(pk=gpes.panel.panel.pk).active_panel.get_gene(gpes.gene.get('gene_symbol'))
        evaluation = gene.evaluation.get(user=self.gel_user)

        assert evaluation.comments.first().comment == comment

        get_comment_url = reverse_lazy('panels:edit_comment_by_user', kwargs={
            'pk': gpes.panel.panel.pk,
            'gene_symbol': gpes.gene.get('gene_symbol'),
            'comment_pk': evaluation.comments.first().pk
        })
        res = self.client.get(get_comment_url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(res.status_code, 200)

        new_comment = fake.sentence()
        edit_comment_url = reverse_lazy('panels:submit_edit_comment_by_user', kwargs={
            'pk': gpes.panel.panel.pk,
            'gene_symbol': gpes.gene.get('gene_symbol'),
            'comment_pk': evaluation.comments.first().pk
        })
        res = self.client.post(edit_comment_url, {'comment': new_comment})
        assert res.status_code == 302
        assert evaluation.comments.first().comment == new_comment

    def test_gene_review_view(self):
        gene = GeneFactory()
        gps = GenePanelSnapshotFactory()
        gpes = GenePanelEntrySnapshotFactory(panel=gps, gene_core=gene)
        url = reverse_lazy('panels:review_gene', args=(gpes.panel.panel.pk, gene.gene_symbol,))
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)

    def test_import_reviews(self):
        gene = GeneFactory(gene_symbol="ABCC5-AS1")
        gps = GenePanelSnapshotFactory()
        gps.panel.name = "Panel One"
        gps.panel.save()
        GenePanelEntrySnapshotFactory.create(gene_core=gene, panel=gps, evaluation=(None,))

        file_path = os.path.join(os.path.dirname(__file__), 'import_reviews_data.tsv')
        test_reviews_file = os.path.abspath(file_path)

        res = None
        with open(test_reviews_file) as f:
            url = reverse_lazy('panels:upload_reviews')
            self.client.post(url, {'review_list': f})

        ap = GenePanel.objects.get(name="Panel One").active_panel
        assert ap.get_gene(gene.gene_symbol).evaluation.count() == 1
