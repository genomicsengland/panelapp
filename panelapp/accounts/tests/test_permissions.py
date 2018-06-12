from django.contrib.auth.models import Group
from accounts.tests.setup import TestMigrations


class PermissionsTest(TestMigrations):
    migrate_from = '0005_auto_20170816_0954'
    migrate_to = '0006_auto_20180612_0937'
    app = 'accounts'

    def test_groups(self):
        self.assertEqual(Group.objects.filter(name='Site Editor').count(), 1)
        self.assertEqual(Group.objects.filter(name='User Support').count(), 1)
        self.assertEqual(Group.objects.filter(name='File Upload Curation').count(), 1)
