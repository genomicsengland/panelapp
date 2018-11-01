import csv
import sys
import djclick as click
from django.db import models
from django.db.models import Case
from django.db.models import Count
from django.db.models import When
from django.db.models import Value
from panels.models import GenePanelSnapshot
from panels.models import Evidence


@click.command()
def command():
    """
    Generate CSV to check which expert reviews need to be updated
    :return:
    """

    header = [
        'Panel Version PK',
        'Panel Name',
        'Panel ID',
        'Panel Version',
        'Panel Status',
        'Last modified',
        'Super panel'
    ]

    writer = csv.writer(sys.stdout)
    writer.writerow(header)

    panels = {}

    for gps in GenePanelSnapshot.objects.all().annotate(child_panels_count=Count('child_panels')).annotate(
            is_super_panel=Case(
                    When(child_panels_count__gt=0, then=Value(True)),
                    default=Value(False),
                    output_field=models.BooleanField()
            )).order_by('panel_id', '-major_version', '-minor_version').iterator():

        key = "{}_{}".format(gps.panel_id, gps.version)
        if key not in panels:
            panels[key] = []

        panel_info = [
            gps.pk,
            gps.panel.name,
            gps.panel.id,
            gps.version,
            gps.panel.status,
            gps.modified,
            gps.is_super_panel
        ]

        panels[key].append(panel_info)

    for panel_id, versions in panels.items():
        if len(versions) > 1:
            for panel_info in versions:


                writer.writerow(panel_info)
