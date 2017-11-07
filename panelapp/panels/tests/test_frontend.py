from random import randint
from django.urls import reverse_lazy
from faker import Factory
from accounts.tests.setup import LoginReviewerUser
from panels.tests.factories import GenePanelEntrySnapshotFactory
from panels.tests.factories import GenePanelSnapshotFactory
from panels.tests.factories import GeneFactory
from panels.models import Evidence
from panels.models import Evaluation
from panels.models import GenePanelEntrySnapshot
from panels.models import Activity


fake = Factory.create()


class TestActivities(LoginReviewerUser):
    def test_activities(self):
        GenePanelEntrySnapshotFactory.create_batch(4)
        res = self.client.get(reverse_lazy('panels:activity'))
        self.assertEqual(res.status_code, 200)

    def test_adding_gene_create_activity(self):
        gps = GenePanelSnapshotFactory()
        GenePanelEntrySnapshotFactory.create_batch(4, panel=gps)
        gene = GeneFactory()

        url = reverse_lazy('panels:add_gene', kwargs={'pk': gps.panel.pk})
        gene_data = {
            "gene": gene.pk,
            "source": Evidence.OTHER_SOURCES[0],
            "phenotypes": "{};{};{}".format(*fake.sentences(nb=3)),
            "rating": Evaluation.RATINGS.AMBER,
            "moi": [x for x in Evaluation.MODES_OF_INHERITANCE][randint(1, 12)][0],
            "mode_of_pathogenicity": [x for x in Evaluation.MODES_OF_PATHOGENICITY][randint(1, 2)][0],
            "penetrance": GenePanelEntrySnapshot.PENETRANCE.Incomplete,
        }
        self.client.post(url, gene_data)

        self.assertEqual(Activity.objects.count(), 1)
