import random
from django.core import mail
from django.contrib.messages import get_messages
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
        self.assertEqual(res.status_code, 302)

        users = User.objects.filter(username=username)
        self.assertEqual(users.count(), 1)
        user = users.first()

        self.assertFalse(user.is_active)

    def test_registration_email(self):
        registration_email(self.external_user.pk)
        self.assertEqual(len(mail.outbox), 1)

    def test_get_email_by_b64_hash(self):
        self.assertEqual(User.objects.get_by_base64_email(self.external_user.base64_email), self.external_user)

    def test_hmac_id(self):
        user = self.external_user

        payload = user.get_crypto_id()
        self.assertTrue(user.verify_crypto_id(payload))

    def test_registration_email_contains_validation_url(self):
        registration_email(self.external_user.pk)
        self.assertIn('/'.join(self.external_user.get_email_verification_url().split('/')[:-2]), mail.outbox[0].body)

    def test_email_validation(self):
        user = self.external_user

        user.is_active = False
        user.save()

        res = self.client.get(user.get_email_verification_url())
        self.assertNotEqual(res.status_code, 404)

    def test_email_validation_link_expired(self):
        user = self.external_user
        user.is_active = False
        user.save()

        with self.settings(ACCOUNT_EMAIL_VERIFICATION_PERIOD=0):
            res = self.client.get(user.get_email_verification_url())
            self.assertEqual(res.status_code, 302)
            message = list(get_messages(res.wsgi_request))[0]
            self.assertEqual(message.message, 'The link has expired. We have sent a new link to your email address.')

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
