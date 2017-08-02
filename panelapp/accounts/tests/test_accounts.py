import random
from django.core import mail
from django.urls import reverse_lazy
from faker import Factory
from accounts.tests.setup import SetupUsers
from accounts.models import User
from accounts.models import Reviewer
from accounts.tasks import registration_email
from accounts.tasks import reviewer_confirmation_requset_email
from accounts.tasks import revierwer_confirmed_email

fake = Factory.create()


class TestUsers(SetupUsers):
    def test_registration(self):
        email = fake.email()
        username = fake.user_name()
        password = fake.sentence()

        data = {
            'username': username,
            'first_name': fake.first_name(),
            'last_name': fake.last_name(),
            'email': email,
            'confirm_email': email,
            'affiliation': fake.word(),
            'role': random.choice([r for r in Reviewer.ROLES])[0],
            'workplace': random.choice([r for r in Reviewer.WORKPLACES])[0],
            'group': random.choice([r for r in Reviewer.GROUPS])[0],
            'password1': password,
            'password2': password,
        }

        res = self.client.post(reverse_lazy('accounts:register'), data)
        assert res.status_code == 302

        assert User.objects.filter(username=username).count() == 1

    def test_registration_email(self):
        registration_email(self.external_user.pk)
        self.assertEqual(len(mail.outbox), 1)

    def test_promote_to_reviewer(self):
        self.external_user.promote_to_reviewer()
        self.assertEqual(self.external_user.reviewer.user_type, Reviewer.TYPES.REVIEWER)

    def test_reviewer_confirmation_request_email(self):
        self.external_user.promote_to_reviewer()
        reviewer_confirmation_requset_email(self.external_user.pk)
        self.assertEqual(len(mail.outbox), 1)

    def test_revierwer_confirmed_email(self):
        revierwer_confirmed_email(self.verified_user.pk)
        self.assertEqual(len(mail.outbox), 1)

    def test_change_password(self):
        username = self.external_user.username
        self.client.login(username=username, password="pass")
        password = fake.sentence()

        data = {
            'current_password': "pass",
            'password1': password,
            'password2': password
        }

        res = self.client.post(reverse_lazy('accounts:change_password'), data)
        assert res.status_code == 302

        assert User.objects.get(username=username).check_password(password) is True

    def test_user_profile(self):
        username = self.external_user.username
        self.client.login(username=username, password="pass")

        res = self.client.get(reverse_lazy('accounts:profile'))
        assert res.status_code == 200
