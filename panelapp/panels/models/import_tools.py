import re
import logging
from more_itertools import unique_everseen
from django.db import models
from django.db import transaction
from model_utils.models import TimeStampedModel
from accounts.models import User
from panels.utils import CellBaseConnector
from panels.exceptions import TSVIncorrectFormat
from panels.exceptions import UserDoesNotExist
from panels.exceptions import GeneDoesNotExist
from panels.utils import remove_non_ascii
from .gene import Gene
from .genepanel import GenePanel
from .genepanelsnapshot import GenePanelSnapshot
from .level4title import Level4Title

logger = logging.getLogger(__name__)


class UploadedGeneList(TimeStampedModel):
    imported = models.BooleanField(default=False)
    gene_list = models.FileField(upload_to='genes')

    def create_genes(self):
        with open(self.gene_list.path) as file:
            logger.info('Started importing list of genes')
            header = file.readline()  # noqa

            with transaction.atomic():
                for line in file:
                    l = line.split("\t")
                    symbol = l[1]
                    name = l[1]
                    OMIM = l[33].split(", ")[0]

                    transcripts = self.get_other_transcripts(symbol)

                    Gene.objects.get_or_create(
                        gene_symbol=symbol,
                        gene_name=name,
                        omim_gene=OMIM,
                        other_transcripts=transcripts
                    )

                    logger.debug("Imported {} gene".format(symbol))

            self.imported = True
            self.save()

    def get_other_transcripts(self, gene_symbol, biotype="protein_coding"):
        connector = CellBaseConnector()
        genes = [gene_symbol.replace("/", "_").replace("#", "")]
        results = [gene for gene in connector.get_coding_transcripts_by_length(genes)]
        logger.debug("{} Received {} results from CellBaseConnector url({})".format(
            gene_symbol, len(results), connector.url)
        )
        transcripts = []
        if len(results) > 0:
            if len(results[0]) > 0:
                all_transcripts = []
                for trn in results[0]:
                    for t in trn["transcripts"]:
                        all_transcripts.append(t)

                transcripts = [t for t in all_transcripts if t["biotype"] == biotype]
                for t in transcripts:
                    t["name"] = t["id"]
                    del t["id"]
        return transcripts


class UploadedPanelList(TimeStampedModel):
    imported = models.BooleanField(default=False)
    panel_list = models.FileField(upload_to='panels')

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
                            'flagged': flagged
                        }
                        if fresh_panel or not active_panel.has_gene(gene_symbol):
                            try:
                                gene = Gene.objects.get(gene_symbol=gene_symbol)
                                name = gene.gene_name
                                other_transcripts = gene.other_transcripts
                                gene_data['gene_name'] = name
                                gene_data['omim'] = omim
                                gene_data['other_transcripts'] = other_transcripts
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
    reviews = models.FileField(upload_to='reviews')

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
                            res = gene.update_evaluation(user, evaluation_data)
                    else:
                        raise UserDoesNotExist(str(i + 2))
                self.imported = True
                self.save()
