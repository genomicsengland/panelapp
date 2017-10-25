from django.test import TestCase
from django.urls import reverse_lazy
from panels.tests.factories import GenePanelEntrySnapshotFactory


class TestActivities(TestCase):
    def test_activities(self):
        GenePanelEntrySnapshotFactory.create_batch(4)
        res = self.client.get(reverse_lazy('panels:activity'))
        self.assertEqual(res.status_code, 200)
