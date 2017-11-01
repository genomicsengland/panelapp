from django.core.management.base import BaseCommand
from django.db import transaction
from panels.models import GenePanelSnapshot
from backups.models import PanelBackup


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        with transaction.atomic():
            for gps in GenePanelSnapshot.objects.iterator():
                try:
                    PanelBackup.objects.get(
                        original_pk=gps.panel.pk,
                        major_version=gps.major_version,
                        minor_version=gps.minor_version
                    )
                except PanelBackup.DoesNotExist:
                    backup_panel = PanelBackup()
                    backup_panel.import_panel(gps)
                    print('Created backup for {} v{}'.format(gps.panel.name, gps.version))
