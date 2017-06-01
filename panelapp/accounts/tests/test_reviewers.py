from django.conf import settings
from django.urls import reverse_lazy
from .setup import SetupUser


class ReviewerTest(SetupUser):
    def setUp(self):
        super().setUp()

    def test_login(self):
        res = self.client.post(reverse_lazy('accounts:login'), {'username': "user", 'password': "pass"})
        assert res.status_code == 302
        self.assertRedirects(res, reverse_lazy(settings.LOGIN_REDIRECT_URL))
