import csv
import sys
import djclick as click
from panels.models import GenePanelSnapshot
from panels.models import Evidence


@click.command()
def command():
    """
    Generate CSV to check which expert reviews need to be updated
    :return:
    """

    header = [
        'Panel Name',
        'Panel ID',
        'Panel Version',
        'Panel Status',
        'Entity Type',
        'Entity',
        'Status',
        'Sources',
        'Change Required',
        'Expert Review'
    ]

    writer = csv.writer(sys.stdout)
    writer.writerow(header)

    for gps in GenePanelSnapshot.objects.get_active_annotated(True, True, True).exclude(is_super_panel=True).iterator():
        panel_info = [
            gps.panel.name,
            gps.panel.id,
            gps.version,
            gps.panel.status
        ]

        for entity in gps.get_all_entities_extra:
            status = entity.saved_gel_status
            sources = entity.evidence.values_list('name', flat=True)
            expert_reviews = [s for s in sources if s in Evidence.EXPERT_REVIEWS]
            change_required = len(expert_reviews) > 1
            expert_review = ''

            if status == 0 and "Expert Review Removed" in expert_reviews:
                expert_review = "Expert Review Removed"
            elif status == 1 and "Expert Review Red" in expert_reviews:
                expert_review = "Expert Review Red"
            elif status == 2 and "Expert Review Amber" in expert_reviews:
                expert_review = "Expert Review Amber"
            elif status > 2 and "Expert Review Green" in expert_reviews:
                expert_review = "Expert Review Green"

            item = [
                *panel_info,
                entity.entity_type,
                entity.entity_name,
                status,
                ';'.join(sources),
                change_required,
                expert_review
            ]

            if change_required:
                writer.writerow(item)
