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
from faker import Factory
from accounts.tests.setup import LoginGELUser
from panels.models import GenePanel
from panels.models import Comment
from panels.models import Evaluation
from panels.tests.factories import TagFactory
from panels.tests.factories import STRFactory
from panels.tests.factories import GeneFactory
from panels.tests.factories import GenePanelSnapshotFactory
from panels.tests.factories import GenePanelEntrySnapshotFactory


fake = Factory.create()


class EvaluationSTRTest(LoginGELUser):
    """Test evaluations"""

    def test_add_evaluation(self):
        """Add an evaluation"""

        str_item = STRFactory()
        str_item.evaluation.all().delete()
        str_item.panel.update_saved_stats()
        url = reverse_lazy(
            "panels:review_entity",
            kwargs={
                "pk": str_item.panel.panel.pk,
                "entity_type": "str",
                "entity_name": str_item.name,
            },
        )

        current_version = str_item.panel.version

        number_of_evaluated_genes = str_item.panel.stats.get("number_of_evaluated_strs")

        str_data = {
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
        res = self.client.post(url, str_data)
        assert res.status_code == 302
        assert (
            number_of_evaluated_genes + 1
            == str_item.panel.panel.active_panel.stats.get("number_of_evaluated_strs")
        )
        assert current_version == str_item.panel.panel.active_panel.version

    def test_add_evaluation_comments_only(self):
        """Add comments"""

        str_item = STRFactory()
        current_version = str_item.panel.version
        str_item.evaluation.all().delete()
        url = reverse_lazy(
            "panels:review_entity",
            kwargs={
                "pk": str_item.panel.panel.pk,
                "entity_type": "str",
                "entity_name": str_item.name,
            },
        )

        str_data = {"comments": fake.sentence()}
        res = self.client.post(url, str_data)
        assert res.status_code == 302

        v01gene = str_item.panel.panel.active_panel.get_str(str_item.name)
        assert v01gene.evaluation.get(user=self.gel_user).comments.count() == 1

        str_data = {"comments": fake.sentence()}
        res = self.client.post(url, str_data)

        assert v01gene.evaluation.get(user=self.gel_user).comments.count() == 2
        assert current_version == str_item.panel.panel.active_panel.version

    def test_user_reviews(self):
        gps = GenePanelSnapshotFactory()
        str_item = STRFactory.create_batch(10, panel=gps)
        for g in str_item:
            for evaluation in g.evaluation.all():
                evaluation.user = self.verified_user
                evaluation.save()

        self.assertEqual(self.verified_user.get_recent_evaluations().count(), 35)

    def test_form_should_be_prefilled(self):
        str_item = STRFactory()
        str_item.evaluation.all().delete()
        url = reverse_lazy(
            "panels:review_entity",
            kwargs={
                "pk": str_item.panel.panel.pk,
                "entity_type": "str",
                "entity_name": str_item.name,
            },
        )

        str_data = {
            "rating": Evaluation.RATINGS.AMBER,
            "current_diagnostic": True,
            "publications": ";".join([fake.sentence(), fake.sentence()]),
            "moi": [x for x in Evaluation.MODES_OF_INHERITANCE][randint(1, 12)][0],
            "mode_of_pathogenicity": [x for x in Evaluation.MODES_OF_PATHOGENICITY][
                randint(1, 2)
            ][0],
        }

        self.client.post(url, str_data)

        url = reverse_lazy(
            "panels:evaluation",
            kwargs={
                "pk": str_item.panel.panel.pk,
                "entity_type": "str",
                "entity_name": str_item.name,
            },
        )
        res = self.client.get(url)
        assert (
            res.content.find(
                str.encode('<option value="{}" selected>'.format(str_data["moi"]))
            )
            != -1
        )

    def test_change_evaluation(self):
        str_item = STRFactory()
        current_version = str_item.panel.version
        str_item.evaluation.all().delete()
        url = reverse_lazy(
            "panels:review_entity",
            kwargs={
                "pk": str_item.panel.panel.pk,
                "entity_type": "str",
                "entity_name": str_item.name,
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
        assert current_version == str_item.panel.panel.active_panel.version

    def test_add_review_after_comment(self):
        """When you add a comment and then want to add a review it should be logged"""

        str_item = STRFactory()
        current_version = str_item.panel.version
        str_item.evaluation.all().delete()
        url = reverse_lazy(
            "panels:review_entity",
            kwargs={
                "pk": str_item.panel.panel.pk,
                "entity_type": "str",
                "entity_name": str_item.name,
            },
        )

        gene_data = {"comments": fake.sentence()}
        res = self.client.post(url, gene_data)
        assert res.status_code == 302

        v01gene = str_item.panel.panel.active_panel.get_str(str_item.name)
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
                "pk": str_item.panel.panel.pk,
                "entity_type": "str",
                "entity_name": str_item.name,
            },
        )
        self.client.post(url_review, review_data)
        res_review = self.client.get(url_review)
        assert res_review.content.find(str.encode(review_data["publications"])) != -1
        assert current_version == str_item.panel.panel.active_panel.version


class STRReviewTest(LoginGELUser):
    def test_mark_as_ready(self):
        str_item = STRFactory()
        str_item.evaluation.all().delete()
        url = reverse_lazy(
            "panels:mark_entity_as_ready",
            kwargs={
                "pk": str_item.panel.panel.pk,
                "entity_type": "str",
                "entity_name": str_item.name,
            },
        )

        self.client.post(url, {"ready_comment": fake.sentence()})
        gene = GenePanel.objects.get(pk=str_item.panel.panel.pk).active_panel.get_str(
            str_item.name
        )
        assert gene.ready is True

    def test_mark_as_ready_no_gene(self):
        str_item = STRFactory(gene=None)
        str_item.evaluation.all().delete()
        url = reverse_lazy(
            "panels:mark_entity_as_ready",
            kwargs={
                "pk": str_item.panel.panel.pk,
                "entity_type": "str",
                "entity_name": str_item.name,
            },
        )

        self.client.post(url, {"ready_comment": fake.sentence()})
        gene = GenePanel.objects.get(pk=str_item.panel.panel.pk).active_panel.get_str(
            str_item.name
        )
        assert gene.ready is True

    def test_update_tags(self):
        str_item = STRFactory()
        current_version = str_item.panel.version
        str_item.evaluation.all().delete()
        url = reverse_lazy(
            "panels:update_entity_tags",
            kwargs={
                "pk": str_item.panel.panel.pk,
                "entity_type": "str",
                "entity_name": str_item.name,
            },
        )

        tag1 = TagFactory()
        tag2 = TagFactory()

        res = self.client.post(
            url, {"tags": [tag1.pk, tag2.pk]}, HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        gene = GenePanel.objects.get(pk=str_item.panel.panel.pk).active_panel.get_str(
            str_item.name
        )
        assert res.json().get("status") == 200
        assert gene.tags.count() == 2
        assert current_version == str_item.panel.panel.active_panel.version

    def test_update_moi(self):
        str_item = STRFactory()
        str_item.evaluation.all().delete()
        url = reverse_lazy(
            "panels:update_entity_moi",
            kwargs={
                "pk": str_item.panel.panel.pk,
                "entity_type": "str",
                "entity_name": str_item.name,
            },
        )

        moi = [x for x in Evaluation.MODES_OF_INHERITANCE][randint(1, 2)]
        data = {"comment": fake.sentence(), "moi": moi[1]}

        res = self.client.post(url, data, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        gene = GenePanel.objects.get(pk=str_item.panel.panel.pk).active_panel.get_str(
            str_item.name
        )
        assert res.json().get("status") == 200
        assert Comment.objects.count() == 1
        assert gene.moi == moi[1]
        assert gene.panel.version != str_item.panel.version

    def test_update_phenotypes(self):
        str_item = STRFactory()
        str_item.evaluation.all().delete()
        url = reverse_lazy(
            "panels:update_entity_phenotypes",
            kwargs={
                "pk": str_item.panel.panel.pk,
                "entity_type": "str",
                "entity_name": str_item.name,
            },
        )

        phenotypes_array = [fake.word(), fake.word()]
        phenotypes = "{}; {}".format(phenotypes_array[0], phenotypes_array[1])
        data = {"comment": fake.sentence(), "phenotypes": phenotypes}

        res = self.client.post(url, data, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        gene = GenePanel.objects.get(pk=str_item.panel.panel.pk).active_panel.get_str(
            str_item.name
        )
        assert res.json().get("status") == 200
        assert Comment.objects.count() == 1
        assert gene.phenotypes == phenotypes_array
        assert gene.panel.version != str_item.panel.version

    def test_update_publications(self):
        str_item = STRFactory()
        str_item.evaluation.all().delete()
        url = reverse_lazy(
            "panels:update_entity_publications",
            kwargs={
                "pk": str_item.panel.panel.pk,
                "entity_type": "str",
                "entity_name": str_item.name,
            },
        )

        publications_array = [fake.word(), fake.word()]
        publications = "{}; {}".format(publications_array[0], publications_array[1])
        data = {"comment": fake.sentence(), "publications": publications}

        res = self.client.post(url, data, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        gene = GenePanel.objects.get(pk=str_item.panel.panel.pk).active_panel.get_str(
            str_item.name
        )
        assert res.json().get("status") == 200
        assert Comment.objects.count() == 1
        assert gene.publications == publications_array
        assert gene.panel.version != str_item.panel.version

    def test_curator_comment_added(self):
        str_item = STRFactory()
        str_item.evaluation.all().delete()
        url = reverse_lazy(
            "panels:update_entity_rating",
            kwargs={
                "pk": str_item.panel.panel.pk,
                "entity_type": "str",
                "entity_name": str_item.name,
            },
        )

        new_status = 0
        data = {"comment": fake.sentence(), "status": new_status}

        res = self.client.post(url, data, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        gene = GenePanel.objects.get(pk=str_item.panel.panel.pk).active_panel.get_str(
            str_item.name
        )

        assert res.content.find(str.encode(data["comment"])) != -1
        assert gene.evaluation.count() > 0

    def test_update_rating(self):
        str_item = STRFactory()
        str_item.evaluation.all().delete()
        url = reverse_lazy(
            "panels:update_entity_rating",
            kwargs={
                "pk": str_item.panel.panel.pk,
                "entity_type": "str",
                "entity_name": str_item.name,
            },
        )

        new_status = 0
        data = {"comment": fake.sentence(), "status": new_status}

        res = self.client.post(url, data, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        gene = GenePanel.objects.get(pk=str_item.panel.panel.pk).active_panel.get_str(
            str_item.name
        )
        assert res.json().get("status") == 200
        assert Comment.objects.count() == 1
        assert res.content.find(str.encode(data["comment"])) != -1
        assert gene.saved_gel_status == new_status

        new_status = 1
        data = {"comment": fake.sentence(), "status": new_status}

        res = self.client.post(url, data, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        gene = GenePanel.objects.get(pk=str_item.panel.panel.pk).active_panel.get_str(
            str_item.name
        )
        assert res.json().get("status") == 200
        assert (
            Comment.objects.count() == 2
        )  # FIXME old comments are deleted even for the current object...
        assert gene.saved_gel_status == new_status

        new_status = 2
        data = {"comment": fake.sentence(), "status": new_status}

        res = self.client.post(url, data, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        gene = GenePanel.objects.get(pk=str_item.panel.panel.pk).active_panel.get_str(
            str_item.name
        )
        assert res.json().get("status") == 200
        assert Comment.objects.count() == 3
        assert gene.saved_gel_status == new_status

        new_status = 3
        data = {"comment": fake.sentence(), "status": new_status}

        res = self.client.post(url, data, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        gene = GenePanel.objects.get(pk=str_item.panel.panel.pk).active_panel.get_str(
            str_item.name
        )
        assert res.json().get("status") == 200
        assert Comment.objects.count() == 4
        assert gene.saved_gel_status == new_status
        assert gene.panel.version != str_item.panel.version

    def test_delete_evaluation(self):
        str_item = STRFactory()
        str_item.evaluation.all().delete()

        evaluation_url = reverse_lazy(
            "panels:review_entity",
            kwargs={
                "pk": str_item.panel.panel.pk,
                "entity_type": "str",
                "entity_name": str_item.name,
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
        gene = GenePanel.objects.get(pk=str_item.panel.panel.pk).active_panel.get_str(
            str_item.name
        )
        assert gene.panel.version == str_item.panel.version
        assert gene.is_reviewd_by_user(self.gel_user) is True

        delete_evaluation_url = reverse_lazy(
            "panels:delete_evaluation_by_user",
            kwargs={
                "pk": str_item.panel.panel.pk,
                "entity_type": "str",
                "entity_name": str_item.name,
                "evaluation_pk": str_item.evaluation.get(user=self.gel_user).pk,
            },
        )
        res = self.client.get(
            delete_evaluation_url, HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        last_gene = GenePanel.objects.get(
            pk=str_item.panel.panel.pk
        ).active_panel.get_str(str_item.name)
        assert res.json().get("status") == 200
        assert last_gene.is_reviewd_by_user(self.gel_user) is False
        assert gene.panel.version == last_gene.panel.version

    def test_delete_comment(self):
        str_item = STRFactory()
        current_version = str_item.panel.version

        evaluation_url = reverse_lazy(
            "panels:review_entity",
            kwargs={
                "pk": str_item.panel.panel.pk,
                "entity_type": "str",
                "entity_name": str_item.name,
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
        gene = GenePanel.objects.get(pk=str_item.panel.panel.pk).active_panel.get_str(
            str_item.name
        )
        evaluation = gene.evaluation.get(user=self.gel_user)

        assert evaluation.comments.count() == 1

        delete_comment_url = reverse_lazy(
            "panels:delete_comment_by_user",
            kwargs={
                "pk": str_item.panel.panel.pk,
                "entity_type": "str",
                "entity_name": str_item.name,
                "comment_pk": evaluation.comments.first().pk,
            },
        )
        res = self.client.get(
            delete_comment_url, HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        assert res.json().get("status") == 200
        assert evaluation.comments.count() == 0
        assert res.content.find(str.encode("Your review")) != -1
        assert current_version == str_item.panel.panel.active_panel.version

    def test_edit_comment(self):
        str_item = STRFactory()
        current_version = str_item.panel.version

        evaluation_url = reverse_lazy(
            "panels:review_entity",
            kwargs={
                "pk": str_item.panel.panel.pk,
                "entity_type": "str",
                "entity_name": str_item.name,
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
        gene = GenePanel.objects.get(pk=str_item.panel.panel.pk).active_panel.get_str(
            str_item.name
        )
        evaluation = gene.evaluation.get(user=self.gel_user)

        assert evaluation.comments.first().comment == comment

        get_comment_url = reverse_lazy(
            "panels:edit_comment_by_user",
            kwargs={
                "pk": str_item.panel.panel.pk,
                "entity_type": "str",
                "entity_name": str_item.name,
                "comment_pk": evaluation.comments.first().pk,
            },
        )
        res = self.client.get(get_comment_url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(res.status_code, 200)

        new_comment = fake.sentence()
        edit_comment_url = reverse_lazy(
            "panels:submit_edit_comment_by_user",
            kwargs={
                "pk": str_item.panel.panel.pk,
                "entity_type": "str",
                "entity_name": str_item.name,
                "comment_pk": evaluation.comments.first().pk,
            },
        )
        res = self.client.post(edit_comment_url, {"comment": new_comment})
        assert res.status_code == 302
        assert evaluation.comments.first().comment == new_comment
        assert current_version == str_item.panel.panel.active_panel.version

    def test_str_review_view(self):
        gene = GeneFactory()
        gps = GenePanelSnapshotFactory()
        str_item = STRFactory(panel=gps, gene_core=gene)
        url = reverse_lazy(
            "panels:review_entity", args=(str_item.panel.panel.pk, "str", str_item.name)
        )
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
