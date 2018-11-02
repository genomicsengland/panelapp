import csv
import djclick as click
from django.db import transaction
from panels.models import Evidence
from panels.models import GenePanelSnapshot


@click.command()
@click.argument('csv_file', type=click.Path(exists=True))
def command(csv_file):
    """
    Go through the file and clear previous expert reviews

    :param csv_file: CSV file with following values:
        'Panel Name', 'Panel ID', 'Panel Version', 'Panel Status', 'Entity Type',
        'Entity', 'Status', 'Sources', 'Change Required', 'Expert Review'
    :return:
    """

    with open(click.format_filename(csv_file), 'r') as f:
        reader = csv.reader(f)
        next(reader)  # skip header

        lines = [line for line in reader if len(line) > 9]

        unique_panels = list({line[1] for line in lines})  # list of unique panel IDs

        with transaction.atomic():
            # go through each panel and create a new version
            panels = {}
            qs = GenePanelSnapshot.objects.get_active_annotated(True, True, True).filter(panel__id__in=unique_panels)
            for p in qs.iterator():
                click.secho('Creating a new version for {}'.format(p), fg='green')
                panels[str(p.panel.id)] = p.increment_version()

            click.secho('Created new versions for {} panels'.format(len(panels)), fg='green')

            for line in lines:
                should_change = line[8].lower() == 'true'
                if should_change:
                    panel = panels[line[1]]
                    entity_type = line[4].strip().lower()
                    entity_name = line[5].strip()
                    keep_expert_review = line[9].strip()

                    entity = None
                    if entity_type == 'gene':
                        entity = panel.get_gene(entity_name, prefetch_extra=True)
                    elif entity_type == 'str':
                        entity = panel.get_str(entity_name, prefetch_extra=True)
                    elif entity_type == 'region':
                        entity = panel.get_region(entity_name, prefetch_extra=True)

                    if entity:
                        keep_evidence = None
                        remove_sources = []

                        for evidence in entity.evidence.all().order_by('-created'):  # most recent first
                            if evidence.name in Evidence.EXPERT_REVIEWS:  # Only remove expert review evidences
                                if evidence.name == keep_expert_review:   # Check for duplicates
                                    if keep_evidence:                     # Already keeping one
                                        remove_sources.append(evidence)
                                    else:
                                        keep_evidence = evidence          # Remove duplicate
                                else:
                                    remove_sources.append(evidence)       # Remove export review

                        if not remove_sources:
                            click.secho('Skipping {}: nothing to remove'.format(panel), fg='red')
                            continue

                        for evidence in remove_sources:
                            entity.evidence.remove(evidence)

                        # make sure current rating still there
                        if not entity.evidence.filter(name=keep_expert_review).count():
                            raise Exception('Entity {} Source {} is missing after cleanup {}'.format(entity, keep_expert_review, panel.pk))

                        # add activity message
                        # not adding TrackRecord as the rating shouldn't change
                        description = "Removed sources: {}".format(', '.join([e.name for e in remove_sources]))
                        panel.add_activity(None, description, entity)
                        click.secho('Cleaned {}: {}'.format(panel, description), fg='green')
                    else:
                        raise Exception('Entity {} is missing in {}'.format(entity_name, panel.pk))

            click.secho('All done', fg='green')
