import logging
from django.db import models
from django.db import transaction
from panels.utils import CellBaseConnector
from .gene import Gene

logger = logging.getLogger(__name__)


class UploadedGeneList(models.Model):
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

                    Gene.objects.create(
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


class UploadedPanelList(models.Model):
    panel_list = models.FileField(upload_to='panels')


class UploadedReviewsList(models.Model):
    reviews = models.FileField(upload_to='reviews')
