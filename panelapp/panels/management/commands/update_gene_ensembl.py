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
import json
import djclick as click
from django.db import transaction
from panels.models import GenePanelSnapshot
from panels.models import GenePanelEntrySnapshot
from panels.models import Region
from panels.models import STR
from panels.models import Gene


@click.command()
@click.argument('json_file', type=click.Path(exists=True))
def command(json_file):
    """
    Update Ensembl IDs in Genes

    This will:

    1. Update Gene data
    2. Increment and panel where this gene is referenced
    3. Update all entities (gene ensembl info) that use this gene

    Runs as a transaction, won't update in case of any failure.

    :param json_file: JSON File in the following format:

    {
      'EXOC3L2': {
        'GRch37': {
          '82': {
            'ensembl_id': 'ENSG00000130201',
            'location': '19:45715879-45737469',
          },
        },
        'GRch38': {
          '90': {
            'ensembl_id': 'ENSG00000283632',
            'location': '19:45212621-45245431',
          },
        },
      },
    }

    A hash of gene symbols and ensembl data from CellBase.

    :return:
    """

    with open(click.format_filename(json_file), 'r') as f:
        json_data = json.load(f)

    process(json_data)

def get_active_panels():
    return GenePanelSnapshot.objects.get_active(all=True, internal=True, superpanels=False) \
        .values_list('pk', flat=True) \
        .distinct()

def process(json_data):
    gene_keys = list(json_data.keys())

    active_panels = get_active_panels()

    unique_panels = set()
    for m in [GenePanelEntrySnapshot, STR, Region]:
        unique_panels.update(
            list(
                m.objects.get_active(pks=active_panels)
                    .filter(gene__gene_symbol__in=gene_keys)
                    .values_list('panel_id', flat=True)
            )
        )

    with transaction.atomic():
        # go through each panel and create a new version
        for gps in GenePanelSnapshot.objects.filter(pk__in=unique_panels):
            gps.increment_version()

        active_panels = get_active_panels()

        # find all genes
        genes_in_panels = GenePanelEntrySnapshot.objects.get_active(pks=active_panels) \
            .filter(gene__gene_symbol__in=gene_keys)
        grouped_genes = {gp.gene_core.gene_symbol: [] for gp in genes_in_panels}
        for gene_in_panel in genes_in_panels:
            grouped_genes[gene_in_panel.gene_core.gene_symbol].append(gene_in_panel)

        strs_in_panels = STR.objects.get_active(pks=active_panels) \
            .filter(gene__gene_symbol__in=gene_keys)
        grouped_strs = {gp.gene_core.gene_symbol: [] for gp in strs_in_panels if gp.gene_core}
        for str_in_panel in strs_in_panels:
            grouped_strs[str_in_panel.gene_core.gene_symbol].append(str_in_panel)

        regions_in_panels = Region.objects.get_active(pks=active_panels) \
            .filter(gene__gene_symbol__in=gene_keys)
        grouped_regions = {gp.gene_core.gene_symbol: [] for gp in regions_in_panels if gp.gene_core}
        for region_in_panel in regions_in_panels:
            grouped_regions[region_in_panel.gene_core.gene_symbol].append(region_in_panel)

        for gene_symbol in gene_keys:
            try:
                gene = Gene.objects.get(gene_symbol=gene_symbol)
            except Gene.DoesNotExist:
                click.secho('Skipping {}. This gene is missing from the db'.format(gene_symbol), fg='red')
                continue

            gene.ensembl_genes = json_data[gene_symbol]
            if not gene.ensembl_genes:
                continue

            gene.save()

            for gene_entry in grouped_genes.get(gene_symbol, []):
                gene_entry.gene_core = gene
                gene_entry.gene = gene.dict_tr()
                gene_entry.save()

            for str_entry in grouped_strs.get(gene_symbol, []):
                str_entry.gene_core = gene
                str_entry.gene = gene.dict_tr()
                str_entry.save()

            for region_entry in grouped_regions.get(gene_symbol, []):
                region_entry.gene_core = gene
                region_entry.gene = gene.dict_tr()
                region_entry.save()

            click.secho("Updated {} Gene Ensembl data".format(gene_symbol), fg='green')

        click.secho('All done', fg='green')