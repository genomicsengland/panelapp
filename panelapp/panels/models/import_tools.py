import json
import re
import csv
import logging
from datetime import datetime
from more_itertools import unique_everseen
from django.db import models
from django.db import transaction
from model_utils.models import TimeStampedModel
from accounts.models import User, Reviewer
from .genepanelentrysnapshot import GenePanelEntrySnapshot
from panels.tasks import import_panel
from panels.tasks import import_reviews
from panels.exceptions import TSVIncorrectFormat
from panels.exceptions import GeneDoesNotExist
from panels.exceptions import UsersDoNotExist
from panels.exceptions import GenesDoNotExist
from .gene import Gene
from .genepanel import GenePanel
from .genepanelsnapshot import GenePanelSnapshot
from .Level4Title import Level4Title
from .codes import ProcessingRunCode


logger = logging.getLogger(__name__)


def update_gene_collection(results):
    with transaction.atomic():
        to_insert = results['insert']
        to_update = results['update']
        to_update_gene_symbol = results['update_symbol']
        to_delete = results['delete']

        for p in GenePanelSnapshot.objects.get_active(all=True):
            p = p.increment_version()

        for record in to_insert:
            new_gene = Gene.from_dict(record)
            if not new_gene.ensembl_genes:
                new_gene.active = False
            new_gene.save()
            logger.debug("Inserted {} gene".format(record['gene_symbol']))

        to_insert = None
        results['insert'] = None

        try:
            user = User.objects.get(username="GEL")
        except User.DoesNotExist:
            user = User.objects.create(username="GEL", first_name="Genomics England")
            Reviewer.objects.create(
                user=user,
                user_type='GEL',
                affiliation='Genomics England',
                workplace='Other',
                role='Other',
                group='Other'
            )

        genes_in_panels = GenePanelEntrySnapshot.objects.get_active()
        grouped_genes = {gp.gene_core.gene_symbol: [] for gp in genes_in_panels}
        for gene_in_panel in genes_in_panels:
            grouped_genes[gene_in_panel.gene_core.gene_symbol].append(gene_in_panel)

        for record in to_update:
            try:
                gene = Gene.objects.get(gene_symbol=record['gene_symbol'])
            except Gene.DoesNotExist:
                gene = Gene(gene_symbol=record['gene_symbol'])

            gene.gene_name = record.get('gene_name', None)
            gene.ensembl_genes = record.get('ensembl_genes', {})
            gene.omim_gene = record.get('omim_gene', [])
            gene.alias = record.get('alias', [])
            gene.biotype = record.get('biotype', 'unknown')
            gene.alias_name = record.get('alias_name', [])
            gene.hgnc_symbol = record['hgnc_symbol']
            gene.hgnc_date_symbol_changed = record.get('hgnc_date_symbol_changed', None)
            gene.hgnc_release = record.get('hgnc_release', None)
            gene.hgnc_id = record.get('hgnc_id', None)
            if not gene.ensembl_genes:
                gene.active = False

            gene.clean_import_dates(record)

            gene.save()

            for gene_entry in grouped_genes.get(record['gene_symbol'], []):
                gene_entry.gene_core = gene
                gene_entry.gene = gene.dict_tr()
                gene_entry.save()
            logger.debug("Updated {} gene".format(record['gene_symbol']))

        grouped_genes = None
        to_update = None
        results['update'] = None

        for record in to_update_gene_symbol:
            active = True
            ensembl_genes = record[0].get('ensembl_genes', {})
            if not ensembl_genes:
                active = False

            # some dates are in the wrong format: %d-%m-%y, Django expects %Y-%m-%-d
            hgnc_date_symbol_changed = record[0].get('hgnc_date_symbol_changed', '')
            if hgnc_date_symbol_changed and len(hgnc_date_symbol_changed) == 8:
                record[0]['hgnc_date_symbol_changed'] = datetime.strptime(hgnc_date_symbol_changed, '%d-%m-%y')

            if record[0].get('hgnc_release', '') and len(record[0].get('hgnc_release', '')) == 8:
                record[0]['hgnc_release'] = datetime.strptime(record[0]['hgnc_release'], '%d-%m-%y')

            try:
                new_gene = Gene.objects.get(gene_symbol=record[0]['gene_symbol'])
            except Gene.DoesNotExist:
                new_gene = Gene()

            # check if record has ensembl genes data if it doesn't and gene has
            # it - keep it as it is and mark gene as active
            if new_gene.pk:
                if not new_gene.ensembl_genes:
                    new_gene.active = active
                    new_gene.ensembl_genes = ensembl_genes
                else:
                    if not ensembl_genes:
                        new_gene.active = True
            else:
                new_gene.active = active
                new_gene.ensembl_genes = ensembl_genes

            new_gene.gene_symbol = record[0]['gene_symbol']
            new_gene.gene_name = record[0].get('gene_name', None)
            new_gene.omim_gene = record[0].get('omim_gene', [])
            new_gene.alias = record[0].get('alias', [])
            new_gene.biotype = record[0].get('biotype', 'unknown')
            new_gene.alias_name = record[0].get('alias_name', [])
            new_gene.hgnc_symbol = record[0]['hgnc_symbol']
            new_gene.hgnc_date_symbol_changed = record[0].get('hgnc_date_symbol_changed', None)
            new_gene.hgnc_release = record[0].get('hgnc_release', None)
            new_gene.hgnc_id = record[0].get('hgnc_id', None)

            new_gene.clean_import_dates(record[0])
            new_gene.save()

            for gene_entry in GenePanelEntrySnapshot.objects.get_active().filter(
                    gene_core__gene_symbol=record[1]):
                panel = gene_entry.panel
                panel.update_gene(user, record[1], {'gene': new_gene})

            try:
                d = Gene.objects.get(gene_symbol=record[1])
                d.active = False
                d.save()
                logger.debug("Updated {} gene. Renamed to {}".format(record[1], record[0]['gene_symbol']))
            except Gene.DoesNotExist:
                logger.debug("Created {} gene. Old gene {} didn't exist".format(record[0]['gene_symbol'], record[1]))

        for record in to_delete:
            gene_in_panels = GenePanelEntrySnapshot.objects.get_active().filter(gene_core__gene_symbol=record)
            if gene_in_panels.count() > 0:
                distinct_panels = gene_in_panels.distinct().values_list('panel__panel__name', flat=True)
                logger.warning("Deleted {} gene, this one is still used in {}".format(record, distinct_panels))

            try:
                old_gene = Gene.objects.get(gene_symbol=record)
                old_gene.active = False
                old_gene.save()
                logger.debug("Deleted {} gene".format(record))
            except Gene.DoesNotExist:
                logger.debug("Didn't delete {} gene - doesn't exist".format(record))

        duplicated_genes = get_duplicated_genes_in_panels()
        if duplicated_genes:
            logger.info('duplicated genes:')
            for g in duplicated_genes:
                logger.info(g)
                print(g)


def get_duplicated_genes_in_panels():
    duplicated_genes = []

    items = GenePanelSnapshot.objects.get_active_anotated(True)
    for item in items:
        dups = set([x for x in item.current_genes if item.current_genes.count(x) > 1])
        if dups:
            duplicated_genes.append((item.pk, item.panel.name, dups))
    return duplicated_genes


class UploadedGeneList(TimeStampedModel):
    imported = models.BooleanField(default=False)
    gene_list = models.FileField(upload_to='genes', max_length=255)

    def create_genes(self):
        with open(self.gene_list.path) as file:
            logger.info('Started importing list of genes')
            results = json.load(file)
            update_gene_collection(results)

            self.imported = True
            self.save()


class UploadedPanelList(TimeStampedModel):
    imported = models.BooleanField(default=False)
    panel_list = models.FileField(upload_to='panels', max_length=255)

    def process_line(self, key, aline, user, active_panel=None, increment_version=False):
        gene_symbol = re.sub("[^0-9a-zA-Z~#_@-]", '', aline[0])
        source = list(unique_everseen([a for a in aline[1].split(";") if a != '']))
        level4 = aline[2].strip(" ")
        level3 = aline[3]
        level2 = aline[4]
        model_of_inheritance = aline[5]
        phenotype = list(unique_everseen([a for a in aline[6].split(";") if a != '']))
        omim = [a for a in aline[7].split(";") if a != '']
        oprahanet = [a for a in aline[8].split(";") if a != '']
        hpo = [a for a in aline[9].split(";") if a != '']
        publication = list(unique_everseen([a for a in aline[10].split(";") if a != '']))
        description = aline[11]
        flagged = True if aline[12] == 'TRUE' else False

        if level4:
            fresh_panel = False
            if not active_panel:
                panel = GenePanel.objects.filter(name=level4).first()
                if not panel:
                    level4_object = Level4Title.objects.create(
                        level2title=level2,
                        level3title=level3,
                        name=level4,
                        description=description,
                        omim=omim,
                        hpo=hpo,
                        orphanet=oprahanet
                    )
                    panel = GenePanel.objects.create(
                        name=level4
                    )
                    GenePanelSnapshot.objects.create(
                        panel=panel,
                        level4title=level4_object,
                        old_panels=[]
                    )
                    fresh_panel = True

                active_panel = panel.active_panel_extra
                if not fresh_panel and increment_version:
                    active_panel = active_panel.increment_version()

            gene_data = {
                'moi': model_of_inheritance,
                'phenotypes': phenotype,
                'publications': publication,
                'sources': source,
                'gene_symbol': gene_symbol,
                'flagged': flagged,
                'omim': omim
            }

            if not active_panel.has_gene(gene_symbol):
                try:
                    Gene.objects.get(gene_symbol=gene_symbol, active=True)
                except Gene.DoesNotExist:
                    raise GeneDoesNotExist("{}, Gene: {}".format(key + 2, gene_symbol))
                active_panel.add_gene(user, gene_symbol, gene_data, False)
            else:
                active_panel.update_gene(user, gene_symbol, gene_data, append_only=True)
            return active_panel
        else:
            raise TSVIncorrectFormat(str(key + 2))

    def process_file(self, user, background=False):
        """Process uploaded file

        If the file has too many lines it wil run the import in the background.abs

        returns ProcessingRunCode
        """

        with open(self.panel_list.path) as file:
            logger.info('Started importing list of genes')
            reader = csv.reader(file, delimiter='\t')
            header = next(reader)  # noqa
            with transaction.atomic():
                active_panel = None
                lines = [line for line in reader]

                if not background and len(lines) > 200:  # panel is too big, process in the background
                    import_panel.delay(user.pk, self.pk)
                    return ProcessingRunCode.PROCESS_BACKGROUND

                first_line = lines[0]
                active_panel = self.process_line(0, first_line, user, active_panel, increment_version=True)

                errors = {
                    'invalid_genes': [],
                    'invalid_lines': []
                }

                for key, line in enumerate(lines[1:]):
                    try:
                        active_panel = self.process_line(key + 1, line, user, active_panel)
                    except GeneDoesNotExist as gene_error:
                        errors['invalid_genes'].append(str(gene_error))
                    except TSVIncorrectFormat as line_error:
                        errors['invalid_lines'].append(str(line_error))

                if errors['invalid_genes']:
                    raise GenesDoNotExist(', '.join(errors['invalid_genes']))

                if errors['invalid_lines']:
                    raise TSVIncorrectFormat(', '.join(errors['invalid_lines']))

                active_panel.update_saved_stats()
                self.imported = True
                self.save()
                return ProcessingRunCode.PROCESSED


class UploadedReviewsList(TimeStampedModel):
    """Review files uploaded by the curation team"""

    imported = models.BooleanField(default=False)
    reviews = models.FileField(upload_to='reviews', max_length=255)

    panels = {}
    database_users = {}

    def process_line(self, key, line):
        """Process individual line"""

        aline = line
        if len(aline) < 21:
            raise TSVIncorrectFormat(str(key + 2))

        gene_symbol = re.sub("[^0-9a-zA-Z~#_@-]", '', aline[0])
        # source = aline[1].split(";")
        level4 = aline[2].rstrip(" ")
        # level3 = aline[3]
        # level2 = aline[4]
        model_of_inheritance = aline[5]
        phenotype = [ph for ph in aline[6].split(";") if ph]
        # omim = aline[7].split(";")
        # oprahanet = aline[8].split(";")
        # hpo = aline[9].split(";")
        publication = [pub for pub in aline[10].split(";") if pub]
        # description = aline[11] # ? What description

        mop = aline[17]
        rate = aline[18]
        current_diagnostic = aline[19]
        if current_diagnostic == "Yes":
            current_diagnostic = True
        else:
            current_diagnostic = False
        comments = aline[20]
        username = aline[21]

        panel = self.panels.get(level4)
        if panel:
            active_panel = panel.active_panel
            if not active_panel.has_gene(gene_symbol):
                raise GeneDoesNotExist("Line: {} Gene: {}".format(key + 2, gene_symbol))

            gene = active_panel.get_gene(gene_symbol)

            evaluation_data = {
                'comment': comments,
                'mode_of_pathogenicity': mop,
                'phenotypes': phenotype,
                'moi': model_of_inheritance,
                'current_diagnostic': current_diagnostic,
                'rating': rate,
                'publications': publication
            }
            user = self.database_users.get(username)
            gene.update_evaluation(user, evaluation_data)

    def process_file(self, user, background=False):
        """Process uploaded file.

        If file has more than 200 lines process it in the background.

        Returns ProcessingRunCode"""

        with open(self.reviews.path) as file:
            logger.info('Started importing list of genes')
            reader = csv.reader(file, delimiter='\t')
            header = next(reader)  # noqa

            with transaction.atomic():
                lines = [line for line in reader]
                users = set([line[21] for line in lines])

                self.database_users = {u.username: u for u in User.objects.filter(username__in=users)}
                non_existing_users = users.symmetric_difference(self.database_users.keys())
                if len(non_existing_users) > 0:
                    raise UsersDoNotExist(", ".join(non_existing_users))

                genes = set([re.sub("[^0-9a-zA-Z~#_@-]", '', line[0]) for line in lines])
                database_genes = Gene.objects.filter(gene_symbol__in=genes).values_list('gene_symbol', flat=True)
                non_existing_genes = genes.symmetric_difference(database_genes)
                if len(non_existing_genes) > 0:
                    raise GenesDoNotExist(", ".join(non_existing_genes))

                panel_names = set([line[2] for line in lines])
                self.panels = {panel.name: panel for panel in GenePanel.objects.filter(name__in=panel_names)}
                for panel in self.panels.values():
                    panel = panel.active_panel.increment_version().panel

                if not background and len(lines) > 20:  # panel is too big, process in the background
                    import_reviews.delay(user.pk, self.pk)
                    return ProcessingRunCode.PROCESS_BACKGROUND

                errors = {
                    'invalid_genes': [],
                    'invalid_lines': []
                }

                for key, line in enumerate(lines):
                    try:
                        self.process_line(key, line)
                    except GeneDoesNotExist as gene_error:
                        errors['invalid_genes'].append(str(gene_error))
                    except TSVIncorrectFormat as line_error:
                        errors['invalid_lines'].append(str(line_error))

                if errors['invalid_genes']:
                    raise GenesDoNotExist(', '.join(errors['invalid_genes']))

                if errors['invalid_lines']:
                    raise TSVIncorrectFormat(', '.join(errors['invalid_lines']))

                self.imported = True
                self.save()
                return ProcessingRunCode.PROCESSED
