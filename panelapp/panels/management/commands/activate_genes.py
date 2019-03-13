##
## Copyright (c) 2016-2019 Genomics England Ltd.
##
## This file is part of PanelApp
## (see https://panelapp.genomicsengland.co.uk).
##
## Licensed to the Apache Software Foundation (ASF) under one
## or more contributor license agreements.  See the NOTICE file
## distributed with this work for additional information
## regarding copyright ownership.  The ASF licenses this file
## to you under the Apache License, Version 2.0 (the
## "License"); you may not use this file except in compliance
## with the License.  You may obtain a copy of the License at
##
##   http://www.apache.org/licenses/LICENSE-2.0
##
## Unless required by applicable law or agreed to in writing,
## software distributed under the License is distributed on an
## "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
## KIND, either express or implied.  See the License for the
## specific language governing permissions and limitations
## under the License.
##
from django.db import transaction
from django.core.management.base import BaseCommand
from panels.models import Gene


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        with transaction.atomic():
            inactive_genes = Gene.objects.filter(active=False)
            self.stdout.write("Found {} inactive genes".format(inactive_genes.count()))
            empty_ensembl_genes = inactive_genes.filter(ensembl_genes="{}")
            self.stdout.write(
                "Found {} inactive genes with empty ensembl_genes".format(
                    empty_ensembl_genes.count()
                )
            )
            self.stdout.write(
                "{} genes should be active".format(
                    inactive_genes.count() - empty_ensembl_genes.count()
                )
            )

            activate = inactive_genes.exclude(
                gene_symbol__in=empty_ensembl_genes.values_list(
                    "gene_symbol", flat=True
                )
            )
            activated_genes = list(activate.values_list("gene_symbol", flat=True))
            activate.update(active=True)
            for gene in activated_genes:
                self.stdout.write("Activated: {}".format(gene))
