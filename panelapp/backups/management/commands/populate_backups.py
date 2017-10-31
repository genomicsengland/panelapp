from django.core.management.base import BaseCommand
from django.db import transaction
from panels.models import GenePanelSnapshot
from backups.models import PanelBackup


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        with transaction.atomic():
            for gps in GenePanelSnapshot.objects.all():
                backup_panel = PanelBackup()
                backup_panel.import_panel(gps)
                print('Created backup for {} v{}'.format(gps.panel.name, gps.version))
