from django.core.management import call_command
from django.test import TestCase
from django.utils.six import StringIO
from panels.tests.factories import GeneFactory
from panels.models import Gene


class ActivateGenesTest(TestCase):
    def test_activate_genes_output(self):
        out = StringIO()

        GeneFactory.create_batch(3, active=True)
        GeneFactory.create_batch(4, active=False, ensembl_genes='{}')
        GeneFactory.create_batch(5, active=False, ensembl_genes='{"hello": "world"}')

        call_command('activate_genes', stdout=out)
        self.assertIn('5 genes should be active', out.getvalue())
        self.assertEqual(8, Gene.objects.filter(active=True).count())
