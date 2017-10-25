from django.test import TransactionTestCase
from django.urls import reverse_lazy


class TestAutocomplete(TransactionTestCase):
    def test_gene(self):
        res = self.client.get(reverse_lazy('autocomplete-gene'))
        self.assertEqual(res.status_code, 200)

    def test_source(self):
        res = self.client.get(reverse_lazy('autocomplete-source'))
        self.assertEqual(res.status_code, 200)

    def test_tags(self):
        res = self.client.get(reverse_lazy('autocomplete-tags'))
        self.assertEqual(res.status_code, 200)
