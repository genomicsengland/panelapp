##
## Copyright (c) 2016-2019 Genomics England Ltd.
##
## This file is part of PanelApp
## (see https://panelapp.genomicsengland.co.uk).
##
## Licensed to the Apache Software Foundation (ASF) under one
## or more contributor license agreements.  See the NOTICE file
## distributed with this work for additional information
## regarding copyright ownership.  The ASF licenses this file
## to you under the Apache License, Version 2.0 (the
## "License"); you may not use this file except in compliance
## with the License.  You may obtain a copy of the License at
##
##   http://www.apache.org/licenses/LICENSE-2.0
##
## Unless required by applicable law or agreed to in writing,
## software distributed under the License is distributed on an
## "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
## KIND, either express or implied.  See the License for the
## specific language governing permissions and limitations
## under the License.
##
import os
from random import randint
from django.urls import reverse_lazy
from django.utils import timezone
from faker import Factory
from accounts.tests.setup import LoginGELUser
from panels.models import GenePanel
from panels.models import Comment
from panels.models import Evaluation
from panels.models import Activity
from panels.tests.factories import TagFactory
from panels.tests.factories import GeneFactory
from panels.tests.factories import GenePanelSnapshotFactory
from panels.tests.factories import GenePanelEntrySnapshotFactory


fake = Factory.create()


class GeneEvaluationTest(LoginGELUser):
    """Test evaluations"""

    def test_add_evaluation(self):
        """Add an evaluation"""

        gpes = GenePanelEntrySnapshotFactory()
        gpes.evaluation.all().delete()
        gpes.panel.update_saved_stats()
        url = reverse_lazy(
            "panels:review_entity",
            kwargs={
                "pk": gpes.panel.panel.pk,
                "entity_type": "gene",
                "entity_name": gpes.gene.get("gene_symbol"),
            },
        )

        current_version = gpes.panel.version

        number_of_evaluated_genes = gpes.panel.stats.get("number_of_evaluated_genes")

        gene_data = {
            "rating": Evaluation.RATINGS.AMBER,
            "current_diagnostic": True,
            "comments": fake.sentence(),
            "publications": ";".join([fake.sentence(), fake.sentence()]),
            "phenotypes": ";".join([fake.sentence(), fake.sentence(), fake.sentence()]),
            "moi": [x for x in Evaluation.MODES_OF_INHERITANCE][randint(1, 12)][0],
            "mode_of_pathogenicity": [x for x in Evaluation.MODES_OF_PATHOGENICITY][
                randint(1, 2)
            ][0],
        }
        res = self.client.post(url, gene_data)
        assert res.status_code == 302
        assert number_of_evaluated_genes + 1 == gpes.panel.panel.active_panel.stats.get(
            "number_of_evaluated_genes"
        )
        assert current_version == gpes.panel.panel.active_panel.version

    def test_add_evaluation_comments_only(self):
        """Add comments"""

        gpes = GenePanelEntrySnapshotFactory()
        current_version = gpes.panel.version
        gpes.evaluation.all().delete()
        url = reverse_lazy(
            "panels:review_entity",
            kwargs={
                "pk": gpes.panel.panel.pk,
                "entity_type": "gene",
                "entity_name": gpes.gene.get("gene_symbol"),
            },
        )

        gene_data = {"comments": fake.sentence()}
        res = self.client.post(url, gene_data)
        assert res.status_code == 302

        v01gene = gpes.panel.panel.active_panel.get_gene(gpes.gene.get("gene_symbol"))
        assert v01gene.evaluation.get(user=self.gel_user).comments.count() == 1

        gene_data = {"comments": fake.sentence()}
        res = self.client.post(url, gene_data)

        assert v01gene.evaluation.get(user=self.gel_user).comments.count() == 2
        assert current_version == gpes.panel.panel.active_panel.version

    def test_add_evaluation_error(self):
        """Add comments"""

        gpes = GenePanelEntrySnapshotFactory()
        current_version = gpes.panel.version
        gpes.evaluation.all().delete()
        url = reverse_lazy(
            "panels:review_entity",
            kwargs={
                "pk": gpes.panel.panel.pk,
                "entity_type": "gene",
                "entity_name": gpes.gene.get("gene_symbol"),
            },
        )

        gene_data = {
            "comments": fake.sentence(),
            "publications": "1;",
            "phenotypes": "2;",
        }
        res = self.client.post(url, gene_data)
        assert res.status_code == 200
        assert b"Make sure there is no ; if no value after: " in res.content

        gene_data = {
            "comments": fake.sentence(),
            "publications": "1",
            "phenotypes": "2",
        }
        res = self.client.post(url, gene_data)
        assert res.status_code == 302

        v01gene = gpes.panel.panel.active_panel.get_gene(gpes.gene.get("gene_symbol"))
        assert v01gene.evaluation.get(user=self.gel_user).comments.count() == 1

    def test_user_reviews(self):
        gps = GenePanelSnapshotFactory()
        gpes = GenePanelEntrySnapshotFactory.create_batch(10, panel=gps)
        for g in gpes:
            for evaluation in g.evaluation.all():
                evaluation.user = self.verified_user
                evaluation.save()

        self.assertEqual(self.verified_user.get_recent_evaluations().count(), 35)

    def test_form_should_be_prefilled(self):
        gpes = GenePanelEntrySnapshotFactory()
        gpes.evaluation.all().delete()
        url = reverse_lazy(
            "panels:review_entity",
            kwargs={
                "pk": gpes.panel.panel.pk,
                "entity_type": "gene",
                "entity_name": gpes.gene.get("gene_symbol"),
            },
        )

        gene_data = {
            "rating": Evaluation.RATINGS.AMBER,
            "current_diagnostic": True,
            "publications": ";".join([fake.sentence(), fake.sentence()]),
            "moi": [x for x in Evaluation.MODES_OF_INHERITANCE][randint(1, 12)][0],
            "mode_of_pathogenicity": [x for x in Evaluation.MODES_OF_PATHOGENICITY][
                randint(1, 2)
            ][0],
        }

        self.client.post(url, gene_data)

        url = reverse_lazy(
            "panels:evaluation",
            kwargs={
                "pk": gpes.panel.panel.pk,
                "entity_type": "gene",
                "entity_name": gpes.gene.get("gene_symbol"),
            },
        )
        res = self.client.get(url)
        assert (
            res.content.find(
                str.encode('<option value="{}" selected>'.format(gene_data["moi"]))
            )
            != -1
        )

    def test_change_evaluation(self):
        gpes = GenePanelEntrySnapshotFactory()
        current_version = gpes.panel.version
        gpes.evaluation.all().delete()
        url = reverse_lazy(
            "panels:review_entity",
            kwargs={
                "pk": gpes.panel.panel.pk,
                "entity_type": "gene",
                "entity_name": gpes.gene.get("gene_symbol"),
            },
        )

        old_phenotypes = [fake.sentence(), fake.sentence(), fake.sentence()]
        gene_data = {
            "rating": Evaluation.RATINGS.AMBER,
            "current_diagnostic": True,
            "comments": fake.sentence(),
            "publications": ";".join([fake.sentence(), fake.sentence()]),
            "phenotypes": ";".join(old_phenotypes),
            "moi": [x for x in Evaluation.MODES_OF_INHERITANCE][randint(1, 12)][0],
            "mode_of_pathogenicity": [x for x in Evaluation.MODES_OF_PATHOGENICITY][
                randint(1, 2)
            ][0],
        }
        self.client.post(url, gene_data)
        assert Evaluation.objects.filter(user=self.gel_user).count() == 1

        gene_data = {
            "moi": [x for x in Evaluation.MODES_OF_INHERITANCE][randint(1, 12)][0],
            "mode_of_pathogenicity": [x for x in Evaluation.MODES_OF_PATHOGENICITY][
                randint(1, 2)
            ][0],
        }
        self.client.post(url, gene_data)
        assert Evaluation.objects.filter(user=self.gel_user).count() == 1
        assert Evaluation.objects.get(user=self.gel_user).phenotypes == old_phenotypes
        assert current_version == gpes.panel.panel.active_panel.version

    def test_add_review_after_comment(self):
        """When you add a comment and then want to add a review it should be logged"""

        gpes = GenePanelEntrySnapshotFactory()
        current_version = gpes.panel.version
        gpes.evaluation.all().delete()
        url = reverse_lazy(
            "panels:review_entity",
            kwargs={
                "pk": gpes.panel.panel.pk,
                "entity_type": "gene",
                "entity_name": gpes.gene.get("gene_symbol"),
            },
        )

        gene_data = {"comments": fake.sentence()}
        res = self.client.post(url, gene_data)
        assert res.status_code == 302

        v01gene = gpes.panel.panel.active_panel.get_gene(gpes.gene.get("gene_symbol"))
        assert v01gene.evaluation.get(user=self.gel_user).comments.count() == 1

        review_data = {
            "rating": Evaluation.RATINGS.AMBER,
            "current_diagnostic": True,
            "comments": fake.sentence(),
            "publications": ";".join([fake.sentence(), fake.sentence()]),
        }
        url_review = reverse_lazy(
            "panels:review_entity",
            kwargs={
                "pk": gpes.panel.panel.pk,
                "entity_type": "gene",
                "entity_name": gpes.gene.get("gene_symbol"),
            },
        )
        self.client.post(url_review, review_data)
        res_review = self.client.get(url_review)
        assert res_review.content.find(str.encode(review_data["publications"])) != -1
        assert current_version == gpes.panel.panel.active_panel.version


class GeneReviewTest(LoginGELUser):
    def test_mark_as_ready(self):
        gpes = GenePanelEntrySnapshotFactory()
        gpes.evaluation.all().delete()
        url = reverse_lazy(
            "panels:mark_entity_as_ready",
            kwargs={
                "pk": gpes.panel.panel.pk,
                "entity_type": "gene",
                "entity_name": gpes.gene.get("gene_symbol"),
            },
        )

        self.client.post(url, {"ready_comment": fake.sentence()})
        gene = GenePanel.objects.get(pk=gpes.panel.panel.pk).active_panel.get_gene(
            gpes.gene.get("gene_symbol")
        )
        assert gene.ready is True

    def test_update_tags(self):
        gpes = GenePanelEntrySnapshotFactory()
        current_version = gpes.panel.version
        gpes.evaluation.all().delete()
        url = reverse_lazy(
            "panels:update_entity_tags",
            kwargs={
                "pk": gpes.panel.panel.pk,
                "entity_type": "gene",
                "entity_name": gpes.gene.get("gene_symbol"),
            },
        )

        tag1 = TagFactory()
        tag2 = TagFactory()

        res = self.client.post(
            url, {"tags": [tag1.pk, tag2.pk]}, HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        gene = GenePanel.objects.get(pk=gpes.panel.panel.pk).active_panel.get_gene(
            gpes.gene.get("gene_symbol")
        )
        assert res.json().get("status") == 200
        assert gene.tags.count() == 2
        assert current_version == gpes.panel.panel.active_panel.version

    def test_update_mop(self):
        gpes = GenePanelEntrySnapshotFactory()
        gpes.evaluation.all().delete()
        url = reverse_lazy(
            "panels:update_entity_mop",
            kwargs={
                "pk": gpes.panel.panel.pk,
                "entity_type": "gene",
                "entity_name": gpes.gene.get("gene_symbol"),
            },
        )

        mop = [x for x in Evaluation.MODES_OF_PATHOGENICITY][randint(1, 2)][0]
        data = {"comment": fake.sentence(), "mode_of_pathogenicity": mop}

        res = self.client.post(url, data, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        gene = GenePanel.objects.get(pk=gpes.panel.panel.pk).active_panel.get_gene(
            gpes.gene.get("gene_symbol")
        )
        assert res.json().get("status") == 200
        assert Comment.objects.count() == 1
        assert gene.mode_of_pathogenicity == mop
        assert gene.panel.version != gpes.panel.version

    def test_update_moi(self):
        gpes = GenePanelEntrySnapshotFactory()
        gpes.evaluation.all().delete()
        url = reverse_lazy(
            "panels:update_entity_moi",
            kwargs={
                "pk": gpes.panel.panel.pk,
                "entity_type": "gene",
                "entity_name": gpes.gene.get("gene_symbol"),
            },
        )

        moi = [x for x in Evaluation.MODES_OF_INHERITANCE][randint(1, 2)][0]
        data = {"comment": fake.sentence(), "moi": moi}

        res = self.client.post(url, data, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        gene = GenePanel.objects.get(pk=gpes.panel.panel.pk).active_panel.get_gene(
            gpes.gene.get("gene_symbol")
        )
        assert res.json().get("status") == 200
        assert Comment.objects.count() == 1
        assert gene.moi == moi
        assert gene.panel.version != gpes.panel.version

    def test_update_phenotypes(self):
        gpes = GenePanelEntrySnapshotFactory()
        gpes.evaluation.all().delete()
        url = reverse_lazy(
            "panels:update_entity_phenotypes",
            kwargs={
                "pk": gpes.panel.panel.pk,
                "entity_type": "gene",
                "entity_name": gpes.gene.get("gene_symbol"),
            },
        )

        phenotypes_array = [fake.word(), fake.word()]
        phenotypes = "{}; {}".format(phenotypes_array[0], phenotypes_array[1])
        data = {"comment": fake.sentence(), "phenotypes": phenotypes}

        res = self.client.post(url, data, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        gene = GenePanel.objects.get(pk=gpes.panel.panel.pk).active_panel.get_gene(
            gpes.gene.get("gene_symbol")
        )
        assert res.json().get("status") == 200
        assert Comment.objects.count() == 1
        assert gene.phenotypes == phenotypes_array
        assert gene.panel.version != gpes.panel.version

    def test_update_phenotypes_add_only(self):
        gpes = GenePanelEntrySnapshotFactory()

        phenotypes_array = [fake.word(), fake.word()]

        old_phenotypes = gpes.phenotypes
        data = {"phenotypes": phenotypes_array}

        ap = GenePanel.objects.get(pk=gpes.panel.panel.pk).active_panel
        ap.update_gene(
            self.gel_user, gpes.gene.get("gene_symbol"), data, append_only=True
        )
        gene = GenePanel.objects.get(pk=gpes.panel.panel.pk).active_panel.get_gene(
            gpes.gene.get("gene_symbol")
        )
        assert gene.phenotypes == list(set(old_phenotypes + phenotypes_array))

    def test_update_publications(self):
        gpes = GenePanelEntrySnapshotFactory()
        gpes.evaluation.all().delete()
        url = reverse_lazy(
            "panels:update_entity_publications",
            kwargs={
                "pk": gpes.panel.panel.pk,
                "entity_type": "gene",
                "entity_name": gpes.gene.get("gene_symbol"),
            },
        )

        publications_array = [fake.word(), fake.word()]
        publications = "{}; {}".format(publications_array[0], publications_array[1])
        data = {"comment": fake.sentence(), "publications": publications}

        res = self.client.post(url, data, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        gene = GenePanel.objects.get(pk=gpes.panel.panel.pk).active_panel.get_gene(
            gpes.gene.get("gene_symbol")
        )
        assert res.json().get("status") == 200
        assert Comment.objects.count() == 1
        assert gene.publications == publications_array
        assert gene.panel.version != gpes.panel.version

    def test_curator_comment_added(self):
        gpes = GenePanelEntrySnapshotFactory()
        gpes.evaluation.all().delete()
        url = reverse_lazy(
            "panels:update_entity_rating",
            kwargs={
                "pk": gpes.panel.panel.pk,
                "entity_type": "gene",
                "entity_name": gpes.gene.get("gene_symbol"),
            },
        )

        new_status = 0
        data = {"comment": fake.sentence(), "status": new_status}

        res = self.client.post(url, data, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        gene = GenePanel.objects.get(pk=gpes.panel.panel.pk).active_panel.get_gene(
            gpes.gene.get("gene_symbol")
        )
        comment = Comment.objects.all()[0]
        assert comment.last_updated
        assert comment.version == gpes.panel.panel.active_panel.version
        assert res.content.find(str.encode(data["comment"])) != -1
        assert gene.evaluation.count() > 0

    def test_comment_unchaged_by_increment(self):
        gps = GenePanelSnapshotFactory()
        gpes = GenePanelEntrySnapshotFactory(panel=gps)
        gpes.evaluation.all().delete()
        url = reverse_lazy(
            "panels:update_entity_rating",
            kwargs={
                "pk": gpes.panel.panel.pk,
                "entity_type": "gene",
                "entity_name": gpes.gene.get("gene_symbol"),
            },
        )

        new_status = 0
        data = {"comment": fake.sentence(), "status": new_status}

        self.client.post(url, data, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        old_comment = Comment.objects.all()[0]
        updated = old_comment.last_updated
        version = old_comment.version

        gps.panel.active_panel.increment_version()
        comment = Comment.objects.all()[0]
        assert comment.last_updated == updated
        assert comment.version == version

    def test_update_rating(self):
        gpes = GenePanelEntrySnapshotFactory()
        gpes.evaluation.all().delete()
        url = reverse_lazy(
            "panels:update_entity_rating",
            kwargs={
                "pk": gpes.panel.panel.pk,
                "entity_type": "gene",
                "entity_name": gpes.gene.get("gene_symbol"),
            },
        )

        new_status = 0
        data = {"comment": fake.sentence(), "status": new_status}

        res = self.client.post(url, data, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        gene = GenePanel.objects.get(pk=gpes.panel.panel.pk).active_panel.get_gene(
            gpes.gene.get("gene_symbol")
        )
        assert res.json().get("status") == 200
        assert Comment.objects.count() == 1
        assert res.content.find(str.encode(data["comment"])) != -1
        assert gene.saved_gel_status == new_status

        new_status = 1
        data = {"comment": fake.sentence(), "status": new_status}

        res = self.client.post(url, data, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        gene = GenePanel.objects.get(pk=gpes.panel.panel.pk).active_panel.get_gene(
            gpes.gene.get("gene_symbol")
        )
        assert res.json().get("status") == 200
        assert Comment.objects.count() == 3
        assert gene.saved_gel_status == new_status

        new_status = 2
        data = {"comment": fake.sentence(), "status": new_status}

        res = self.client.post(url, data, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        gene = GenePanel.objects.get(pk=gpes.panel.panel.pk).active_panel.get_gene(
            gpes.gene.get("gene_symbol")
        )
        assert res.json().get("status") == 200
        assert Comment.objects.count() == 6
        assert gene.saved_gel_status == new_status

        new_status = 3
        data = {"comment": fake.sentence(), "status": new_status}

        res = self.client.post(url, data, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        gene = GenePanel.objects.get(pk=gpes.panel.panel.pk).active_panel.get_gene(
            gpes.gene.get("gene_symbol")
        )
        assert res.json().get("status") == 200
        assert Comment.objects.count() == 10
        assert gene.saved_gel_status == new_status
        assert gene.panel.version != gpes.panel.version

    def test_delete_evaluation(self):
        gpes = GenePanelEntrySnapshotFactory()
        gpes.evaluation.all().delete()

        evaluation_url = reverse_lazy(
            "panels:review_entity",
            kwargs={
                "pk": gpes.panel.panel.pk,
                "entity_type": "gene",
                "entity_name": gpes.gene.get("gene_symbol"),
            },
        )

        gene_data = {
            "rating": Evaluation.RATINGS.AMBER,
            "current_diagnostic": True,
            "comments": fake.sentence(),
            "publications": ";".join([fake.sentence(), fake.sentence()]),
            "phenotypes": ";".join([fake.sentence(), fake.sentence(), fake.sentence()]),
            "moi": [x for x in Evaluation.MODES_OF_INHERITANCE][randint(1, 12)][0],
            "mode_of_pathogenicity": [x for x in Evaluation.MODES_OF_PATHOGENICITY][
                randint(1, 2)
            ][0],
        }
        self.client.post(
            evaluation_url, gene_data, HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        gene = GenePanel.objects.get(pk=gpes.panel.panel.pk).active_panel.get_gene(
            gpes.gene.get("gene_symbol")
        )
        assert gene.panel.version == gpes.panel.version
        assert gene.is_reviewd_by_user(self.gel_user) is True

        delete_evaluation_url = reverse_lazy(
            "panels:delete_evaluation_by_user",
            kwargs={
                "pk": gpes.panel.panel.pk,
                "entity_type": "gene",
                "entity_name": gpes.gene.get("gene_symbol"),
                "evaluation_pk": gene.evaluation.get(user=self.gel_user).pk,
            },
        )
        res = self.client.get(
            delete_evaluation_url, HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        last_gene = GenePanel.objects.get(pk=gpes.panel.panel.pk).active_panel.get_gene(
            gpes.gene.get("gene_symbol")
        )
        assert res.json().get("status") == 200
        assert last_gene.is_reviewd_by_user(self.gel_user) is False
        assert gene.panel.version == last_gene.panel.version

    def test_delete_comment(self):
        gpes = GenePanelEntrySnapshotFactory()
        current_version = gpes.panel.version

        evaluation_url = reverse_lazy(
            "panels:review_entity",
            kwargs={
                "pk": gpes.panel.panel.pk,
                "entity_type": "gene",
                "entity_name": gpes.gene.get("gene_symbol"),
            },
        )

        gene_data = {
            "rating": Evaluation.RATINGS.AMBER,
            "current_diagnostic": True,
            "comments": fake.sentence(),
            "publications": ";".join([fake.sentence(), fake.sentence()]),
            "phenotypes": ";".join([fake.sentence(), fake.sentence(), fake.sentence()]),
            "moi": [x for x in Evaluation.MODES_OF_INHERITANCE][randint(1, 12)][0],
            "mode_of_pathogenicity": [x for x in Evaluation.MODES_OF_PATHOGENICITY][
                randint(1, 2)
            ][0],
        }
        self.client.post(
            evaluation_url, gene_data, HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        gene = GenePanel.objects.get(pk=gpes.panel.panel.pk).active_panel.get_gene(
            gpes.gene.get("gene_symbol")
        )
        evaluation = gene.evaluation.get(user=self.gel_user)

        assert evaluation.comments.count() == 1

        delete_comment_url = reverse_lazy(
            "panels:delete_comment_by_user",
            kwargs={
                "pk": gpes.panel.panel.pk,
                "entity_type": "gene",
                "entity_name": gpes.gene.get("gene_symbol"),
                "comment_pk": evaluation.comments.first().pk,
            },
        )
        res = self.client.get(
            delete_comment_url, HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        assert res.json().get("status") == 200
        assert evaluation.comments.count() == 0
        assert res.content.find(str.encode("Your review")) != -1
        assert current_version == gpes.panel.panel.active_panel.version

    def test_edit_comment(self):
        gpes = GenePanelEntrySnapshotFactory()
        current_version = gpes.panel.version

        evaluation_url = reverse_lazy(
            "panels:review_entity",
            kwargs={
                "pk": gpes.panel.panel.pk,
                "entity_type": "gene",
                "entity_name": gpes.gene.get("gene_symbol"),
            },
        )

        comment = fake.sentence()

        gene_data = {
            "rating": Evaluation.RATINGS.AMBER,
            "current_diagnostic": True,
            "comments": comment,
            "publications": ";".join([fake.sentence(), fake.sentence()]),
            "phenotypes": ";".join([fake.sentence(), fake.sentence(), fake.sentence()]),
            "moi": [x for x in Evaluation.MODES_OF_INHERITANCE][randint(1, 12)][0],
            "mode_of_pathogenicity": [x for x in Evaluation.MODES_OF_PATHOGENICITY][
                randint(1, 2)
            ][0],
        }
        self.client.post(
            evaluation_url, gene_data, HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        gene = GenePanel.objects.get(pk=gpes.panel.panel.pk).active_panel.get_gene(
            gpes.gene.get("gene_symbol")
        )
        evaluation = gene.evaluation.get(user=self.gel_user)

        assert evaluation.comments.first().comment == comment

        get_comment_url = reverse_lazy(
            "panels:edit_comment_by_user",
            kwargs={
                "pk": gpes.panel.panel.pk,
                "entity_type": "gene",
                "entity_name": gpes.gene.get("gene_symbol"),
                "comment_pk": evaluation.comments.first().pk,
            },
        )
        res = self.client.get(get_comment_url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(res.status_code, 200)

        created = timezone.now()

        new_comment = fake.sentence()
        edit_comment_url = reverse_lazy(
            "panels:submit_edit_comment_by_user",
            kwargs={
                "pk": gpes.panel.panel.pk,
                "entity_type": "gene",
                "entity_name": gpes.gene.get("gene_symbol"),
                "comment_pk": evaluation.comments.first().pk,
            },
        )
        res = self.client.post(edit_comment_url, {"comment": new_comment})
        activity = Activity.objects.all()[0]
        comment = evaluation.comments.first()
        assert comment.version == gpes.panel.panel.active_panel.version
        assert comment.last_updated > created
        assert res.status_code == 302
        assert evaluation.comments.first().comment == new_comment
        assert current_version == gpes.panel.panel.active_panel.version
        assert "changed review comment from" in activity.text

    def test_gene_review_view(self):
        gene = GeneFactory()
        gps = GenePanelSnapshotFactory()
        gpes = GenePanelEntrySnapshotFactory(panel=gps, gene_core=gene)
        url = reverse_lazy(
            "panels:review_entity", args=(gpes.panel.panel.pk, "gene", gene.gene_symbol)
        )
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)

    def test_import_reviews(self):
        gene = GeneFactory(gene_symbol="ABCC5-AS1")
        gps = GenePanelSnapshotFactory()
        current_version = gps.version
        gps.panel.name = "Panel One"
        gps.panel.save()
        GenePanelEntrySnapshotFactory.create(
            gene_core=gene, panel=gps, evaluation=(None,)
        )

        file_path = os.path.join(os.path.dirname(__file__), "import_reviews_data.tsv")
        test_reviews_file = os.path.abspath(file_path)

        with open(test_reviews_file) as f:
            url = reverse_lazy("panels:upload_reviews")
            self.client.post(url, {"review_list": f})

        ap = GenePanel.objects.get(name="Panel One").active_panel
        assert ap.get_gene(gene.gene_symbol).evaluation.count() == 1
        assert current_version != ap.version
