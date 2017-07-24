from django.test import TransactionTestCase
from panels.templatetags.panel_helpers import pubmed_link
from panels.templatetags.panel_helpers import evaluation_rating_class
from panels.templatetags.panel_helpers import human_issue_type
from panels.models import Evaluation
from panels.models import TrackRecord
from .factories import EvaluationFactory
from .factories import TrackRecordFactory


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
