import csv
import djclick as click
from django.db import transaction
from panels.models import GenePanel
from panels.models import PanelType


@click.command()
@click.argument('csv_file', type=click.Path(exists=True))
def command(csv_file):
    panel_types = {t.slug: t for t in PanelType.objects.all()}
    gene_panels = {str(p.pk): p for p in GenePanel.objects.all().prefetch_related('types')}

    with open(click.format_filename(csv_file), 'r') as f:
        reader = csv.reader(f)
        next(reader)  # skip header

        with transaction.atomic():
            error_lines = []

            for index, line in enumerate(reader):
                if line and len(line) == 2:
                    panel_id, slug = line
                    panel = gene_panels.get(panel_id, None)
                    panel_type = panel_types.get(slug, None)

                    if not panel or not panel_type:
                        if not panel:
                            click.secho('[{}] Cant find panel with id: {}'.format(index + 1, panel_id), err=True, fg='red')
                        if not panel_type:
                            click.secho('[{}] Cant find panel_type with slug: {}'.format(index + 1, slug), err=True, fg='red')
                        error_lines.append([index, panel_id, slug])
                        continue

                    panel.types.add(panel_type)  # it won't duplicate

                else:
                    click.secho('[{}] Skipping line, incorrect format'.format(index + 1))

            if error_lines:
                click.secho('Couldn\'t assign {} records'.format(len(error_lines)))
            else:
                click.secho('All done', fg='green')
