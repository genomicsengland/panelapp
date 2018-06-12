from django.db.migrations.executor import MigrationExecutor
from django.db import connection
from django.test import TransactionTestCase
from faker import Factory
from accounts.models import Reviewer
from .factories import UserFactory


fake = Factory.create()


class SetupUsers(TransactionTestCase):
    """
    Setup base User and their Reviewer models
    """

    def setUp(self):
        super().setUp()

        self.gel_user = UserFactory(username="gel_user", reviewer__user_type=Reviewer.TYPES.GEL)
        self.verified_user = UserFactory(username="verified_user", reviewer__user_type=Reviewer.TYPES.REVIEWER)
        self.external_user = UserFactory(username="external_user")


class LoginReviewerUser(SetupUsers):
    """
    LoginGELUser sets up session data on the default Client object available via
    self.client, so in the later tests we don't need to authorise before we make
    the requests.
    """

    def setUp(self):
        super().setUp()
        login_res = self.client.login(username="verified_user", password="pass")
        assert login_res is True


class LoginGELUser(SetupUsers):
    """
    LoginGELUser sets up session data on the default Client object available via
    self.client, so in the later tests we don't need to authorise before we make
    the requests.
    """

    def setUp(self):
        super().setUp()
        login_res = self.client.login(username="gel_user", password="pass")
        assert login_res is True


class TestMigrations(TransactionTestCase):
    migrate_from = None
    migrate_to = None
    app = None

    def setUp(self):
        assert self.migrate_from and self.migrate_to and self.app, \
            "TestCase '{}' must define app, migrate_from and migrate_to properties".format(self.__class__.__name__)
        self.migrate_from = [(self.app, self.migrate_from)]
        self.migrate_to = [(self.app, self.migrate_to)]
        executor = MigrationExecutor(connection)
        old_apps = executor.loader.project_state(self.migrate_from).apps

        # Reverse to the original migration
        executor.migrate(self.migrate_from)

        self.setUpBeforeMigration(old_apps)

        # Run the migration to test
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()  # reload.
        executor.migrate(self.migrate_to)

        self.apps = executor.loader.project_state(self.migrate_to).apps

    def setUpBeforeMigration(self, apps):
        pass