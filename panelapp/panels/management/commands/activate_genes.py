from django.db import transaction
from django.core.management.base import BaseCommand
from panels.models import Gene


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        with transaction.atomic():
            inactive_genes = Gene.objects.filter(active=False)
            self.stdout.write('Found {} inactive genes'.format(inactive_genes.count()))
            empty_ensembl_genes = inactive_genes.filter(ensembl_genes='{}')
            self.stdout.write('Found {} inactive genes with empty ensembl_genes'.format(empty_ensembl_genes.count()))
            self.stdout.write('{} genes should be active'.format(inactive_genes.count() - empty_ensembl_genes.count()))

            activate = inactive_genes.exclude(gene_symbol__in=empty_ensembl_genes.values_list('gene_symbol', flat=True))
            activated_genes = list(activate.values_list('gene_symbol', flat=True))
            activate.update(active=True)
            for gene in activated_genes:
                self.stdout.write('Activated: {}'.format(gene))
