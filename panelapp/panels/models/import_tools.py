import json
import re
import logging
from datetime import datetime
from more_itertools import unique_everseen
from django.db import models
from django.db import transaction
from model_utils.models import TimeStampedModel
from accounts.models import User
from .genepanelentrysnapshot import GenePanelEntrySnapshot
from panels.utils import CellBaseConnector
from panels.exceptions import TSVIncorrectFormat
from panels.exceptions import UserDoesNotExist
from panels.exceptions import GeneDoesNotExist
from panels.utils import remove_non_ascii
from .gene import Gene
from .genepanel import GenePanel
from .genepanelsnapshot import GenePanelSnapshot
from .Level4Title import Level4Title

logger = logging.getLogger(__name__)


def update_gene_collection(results):
    with transaction.atomic():
        to_insert = results['insert']
        to_update = results['update']
        to_update_gene_symbol = results['update_symbol']
        to_delete = results['delete']
        for p in GenePanelSnapshot.objects.get_active(all=True):
            p.increment_version()

        for record in to_insert:
            new_gene = Gene.from_dict(record)
            if not new_gene.ensembl_genes:
                new_gene.active = False
            new_gene.save()
            logger.debug("Inserted {} gene".format(record['gene_symbol']))

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
            for gene_entry in GenePanelEntrySnapshot.objects.get_active().filter(
                    gene_core__gene_symbol=record['gene_symbol']):
                gene_entry.gene_core = gene
                gene_entry.gene = gene.dict_tr()
                gene_entry.save()
            logger.debug("Updated {} gene".format(record['gene_symbol']))

        for record in to_update_gene_symbol:
            active = True
            if not record[0].get('ensembl_genes', {}):
                active = False
            
            # some dates are in the wrong format: %d-%m-%y, Django expects %Y-%m-%-d
            if record[0].get('hgnc_date_symbol_changed', '') and  len(record[0].get('hgnc_date_symbol_changed', '')) == 8:
                record[0]['hgnc_date_symbol_changed'] = datetime.strptime(record[0]['hgnc_date_symbol_changed'], '%d-%m-%y')

            if record[0].get('hgnc_release', '') and len(record[0].get('hgnc_release', '')) == 8:
                record[0]['hgnc_release'] = datetime.strptime(record[0]['hgnc_release'], '%d-%m-%y')

            try:
                new_gene = Gene.objects.get(gene_symbol=record[0]['gene_symbol'])
            except Gene.DoesNotExist:
                new_gene = Gene()

            new_gene.gene_symbol = record[0]['gene_symbol']
            new_gene.gene_name = record[0].get('gene_name', None)
            new_gene.ensembl_genes = record[0].get('ensembl_genes', {})
            new_gene.omim_gene = record[0].get('omim_gene', [])
            new_gene.alias = record[0].get('alias', [])
            new_gene.biotype = record[0].get('biotype', 'unknown')
            new_gene.alias_name = record[0].get('alias_name', [])
            new_gene.hgnc_symbol = record[0]['hgnc_symbol']
            new_gene.hgnc_date_symbol_changed = record[0].get('hgnc_date_symbol_changed', None)
            new_gene.hgnc_release = record[0].get('hgnc_release', None)
            new_gene.hgnc_id = record[0].get('hgnc_id', None)
            new_gene.active = active

            new_gene.clean_import_dates(record[0])
            new_gene.save()
            
            for gene_entry in GenePanelEntrySnapshot.objects.get_active().filter(
                    gene_core__gene_symbol=record[1]):
                gene_entry.gene_core = new_gene
                gene_entry.gene = new_gene.dict_tr()
                gene_entry.save()
            
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

    def process_file(self, user):
        with open(self.panel_list.path) as file:
            logger.info('Started importing list of genes')
            header = file.readline()  # noqa
            with transaction.atomic():
                active_panel = None
                for i, line in enumerate(file):
                    line = remove_non_ascii(line)
                    aline = line.replace('"', "").rstrip("\n").split("\t")
                    gene_symbol = re.sub("[^0-9a-zA-Z~#_@-]", '', aline[0])
                    source = list(unique_everseen(aline[1].split(";")))
                    level4 = aline[2].rstrip(" ")
                    level3 = aline[3]
                    level2 = aline[4]
                    model_of_inheritance = aline[6]
                    phenotype = list(unique_everseen(aline[7].split(";")))
                    omim = aline[8].split(";")
                    oprahanet = aline[9].split(";")
                    hpo = aline[10].split(";")
                    publication = list(unique_everseen(aline[11].split(";")))
                    description = aline[12]
                    flagged = aline[13]

                    if level4:
                        fresh_panel = False
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
                                level4title=level4_object
                            )
                            fresh_panel = True

                        active_panel = panel.active_panel

                        gene_data = {
                            'moi': model_of_inheritance,
                            'phenotypes': phenotype,
                            'publications': publication,
                            'sources': source,
                            'gene_symbol': gene_symbol,
                            'flagged': flagged,
                            'omim': omim
                        }
                        if fresh_panel or not active_panel.has_gene(gene_symbol):
                            try:
                                Gene.objects.get(gene_symbol=gene_symbol, active=True)
                            except Gene.DoesNotExist:
                                raise GeneDoesNotExist(str(i + 2))
                            active_panel.add_gene(user, gene_symbol, gene_data)
                        else:
                            active_panel.update_gene(user, gene_symbol, gene_data)
                    else:
                        raise TSVIncorrectFormat(str(i + 2))
            self.imported = True
            self.save()


class UploadedReviewsList(TimeStampedModel):
    imported = models.BooleanField(default=False)
    reviews = models.FileField(upload_to='reviews', max_length=255)

    def process_file(self):
        with open(self.reviews.path) as file:
            logger.info('Started importing list of genes')
            header = file.readline()  # noqa
            with transaction.atomic():
                for i, line in enumerate(file):
                    line = re.sub(r'[^\x00-\x7F]+', ' ', line)
                    aline = line.replace('"', "").rstrip("\n").split("\t")
                    if len(aline) < 22:
                        raise TSVIncorrectFormat(str(i + 2))

                    gene_symbol = re.sub("[^0-9a-zA-Z~#_@-]", '', aline[0])
                    # source = aline[1].split(";")
                    level4 = aline[2].rstrip(" ")
                    # level3 = aline[3]
                    # level2 = aline[4]
                    # transcript = aline[5]
                    model_of_inheritance = aline[6]
                    phenotype = aline[7].split(";")
                    # omim = aline[8].split(";")
                    # oprahanet = aline[9].split(";")
                    # hpo = aline[10].split(";")
                    publication = aline[11].split(";")
                    # description = aline[12] # ? What description

                    mop = aline[17]
                    rate = aline[18]
                    current_diagnostic = aline[19]
                    if current_diagnostic == "Yes":
                        current_diagnostic = True
                    else:
                        current_diagnostic = False
                    comments = aline[20]
                    username = aline[21]

                    user = User.objects.filter(username=username).first()
                    if user:
                        panels = GenePanel.objects.filter(name=level4)
                        if len(panels) == 1:
                            panel = panels[0].active_panel
                            gene = panel.get_gene(gene_symbol)
                            if not gene:
                                raise GeneDoesNotExist(str(i + 2))

                            evaluation_data = {
                                'comment': comments,
                                'mode_of_pathogenicity': mop,
                                'phenotypes': phenotype,
                                'moi': model_of_inheritance,
                                'current_diagnostic': current_diagnostic,
                                'rating': rate,
                                'publications': publication
                            }
                            gene.update_evaluation(user, evaluation_data)
                    else:
                        raise UserDoesNotExist(str(i + 2))
                self.imported = True
                self.save()
