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
from django.test import TransactionTestCase
from panels.templatetags.panel_helpers import pubmed_link
from panels.templatetags.panel_helpers import evaluation_rating_class
from panels.templatetags.panel_helpers import human_issue_type
from panels.models import Evaluation
from panels.models import TrackRecord
from panels.tests.factories import EvaluationFactory
from panels.tests.factories import TrackRecordFactory


class TestTemplatetags(TransactionTestCase):
    def test_pubmed_link(self):
        l = pubmed_link('1234567')
        assert l != '1234567'

    def test_evaluation_rating_class(self):
        red = EvaluationFactory(rating=Evaluation.RATINGS.RED)
        amber = EvaluationFactory(rating=Evaluation.RATINGS.AMBER)
        green = EvaluationFactory(rating=Evaluation.RATINGS.GREEN)

        assert evaluation_rating_class(red) == 'gel-red'
        assert evaluation_rating_class(amber) == 'gel-amber'
        assert evaluation_rating_class(green) == 'gel-green'

    def test_human_issue_type(self):
        tr = TrackRecordFactory(issue_type=TrackRecord.ISSUE_TYPES.NewSource)
        assert human_issue_type(tr.issue_type) == "Added New Source"
