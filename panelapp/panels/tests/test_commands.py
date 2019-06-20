from random import randint
from django.urls import reverse_lazy
from faker import Factory
from django.core.management import call_command
from accounts.tests.setup import LoginGELUser
from panels.models import GenePanelSnapshot, GenePanelEntrySnapshot
from panels.models import Evidence
from panels.models import Evaluation
from panels.tests.factories import GeneFactory
from panels.tests.factories import GenePanelSnapshotFactory

fake = Factory.create()


class CommandTest(LoginGELUser):
    def test_fix_gel_status(self):
        gene = GeneFactory()
        gps = GenePanelSnapshotFactory()
        url = reverse_lazy(
            "panels:add_entity", kwargs={"pk": gps.panel.pk, "entity_type": "gene"}
        )
        gene_data = {
            "gene": gene.pk,
            "source": Evidence.OTHER_SOURCES[0],
            "phenotypes": "{};{};{}".format(*fake.sentences(nb=3)),
            "rating": Evaluation.RATINGS.AMBER,
            "moi": [x for x in Evaluation.MODES_OF_INHERITANCE][randint(1, 12)][0],
            "mode_of_pathogenicity": [x for x in Evaluation.MODES_OF_PATHOGENICITY][
                randint(1, 2)
            ][0],
            "penetrance": GenePanelEntrySnapshot.PENETRANCE.Incomplete,
        }
        self.client.post(url, gene_data)
        panel = gps.panel.active_panel

        gene = panel.get_gene(gene.gene_symbol)
        gene.saved_gel_status = 4
        gene.save()
        call_command("fix_gel_status")
        panel = GenePanelSnapshot.objects.get_active(
            all=True, internal=True, superpanels=False
        )[0]

        assert panel.genepanelentrysnapshot_set.all()[0].saved_gel_status == 3
