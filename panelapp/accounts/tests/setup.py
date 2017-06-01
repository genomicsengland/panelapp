from django.urls import reverse_lazy
from django.test import TestCase
from django.test import Client
from faker import Factory
from accounts.models import User
from accounts.models import Reviewer


fake = Factory.create()


class SetupUser(TestCase):
    def setUp(self):
        super().setUp()

        self.gel_user = self.create_user("user")
        self.gel_reviewer = self.create_reviewer(self.gel_user)

        self.external_user = self.create_user("external")
        self.external_reviewer = self.create_reviewer(self.external_user, Reviewer.TYPES.EXTERNAL)

    def create_reviewer(self, user, user_type=None):
        user_type = user_type or Reviewer.TYPES.GEL
        return Reviewer.objects.create(
            user=user,
            user_type=user_type,
            workplace=Reviewer.WORKPLACES['Industry'],
            group=Reviewer.GROUPS['Other'],
            role=Reviewer.ROLES['Other'],
            affiliation="some affiliation"
        )

    def create_user(self, username):
        username = username or fake.user_name()

        u = User.objects.create(
            email=fake.email(),
            first_name=fake.first_name(),
            last_name=fake.last_name(),
            username=username,
            is_active=True
        )
        u.set_password("pass")
        u.save()
        return u


class LoginUser(SetupUser):
    def setUp(self):
        super().setUp()
        login_res = self.client.login(username="user", password="pass")
        assert login_res == True
