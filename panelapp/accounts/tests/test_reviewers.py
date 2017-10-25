from django.conf import settings
from django.urls import reverse_lazy
from accounts.tests.setup import SetupUsers


class ReviewerTest(SetupUsers):
    def setUp(self):
        super().setUp()

    def test_login(self):
        res = self.client.post(reverse_lazy('accounts:login'), {'username': "external_user", 'password': "pass"})
        assert res.status_code == 302
        self.assertRedirects(res, reverse_lazy(settings.LOGIN_REDIRECT_URL))
