#!/usr/bin/env python3
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
"""
Import dates and versions for evaluations which had no previous dates.

Required:
    This script required the same environemnt variables as other python django commands,
    i.e. DJANGO_SETTINGS_MODULE, DATABASE_URL, etc.

    The first parameter for the script is the location of TSV file with missing
    evaluations metadata.

Example:
    `DJANGO_LOG_LEVEL=WARNING scripts/populate_missing_evaluation_dates.py 
    scripts/missing-evaluation-dates.tsv`

Author Oleg Gerasimenko
(c) 2017 Genomics England
Internal
"""

import os
import sys
import csv
import django

sys.path.insert(0, os.path.abspath(os.path.curdir))
django.setup()
from panels.models import GenePanelEntrySnapshot

assert len(sys.argv) > 1

from django.db import transaction
from panels.models import GenePanelSnapshot

missing_data = {}
with open(sys.argv[1], "r") as f:
    reader = csv.reader(f, delimiter="\t")
    for row in reader:
        # panel id, gene symbol, username, panel version, date time
        if not missing_data.get(row[0]):
            missing_data[row[0]] = {}
        if not missing_data[row[0]].get(row[1]):
            missing_data[row[0]][row[1]] = {}
        missing_data[row[0]][row[1]][row[2]] = {"version": row[3], "date": row[4]}

# Some gene symbols changed, this is the mapping Louise found
new_genes = {
    "ADCK3": "COQ8A",
    "B3GALTL": "B3GLCT",
    "CCDC23": "SVBP",
    "DDX26B": "INTS6L",
    "DFNB31": "WHRN",
    "DLG4": "LLGL1",
    "DYX1C1": "DNAAF4",
    "ENTHD2": "TEPSIN",
    "ERF": "ETF1",
    "FAM134B": "RETREG1",
    "GSS": "PRNP",
    "HDHD1": "PUDP",
    "KAL1": "ANOS1",
    "KIAA0196": "WASHC5",
    "KIAA0226": "RUBCN",
    "LAMB2": "LAMC1",
    "LARGE": "LARGE1",
    "MRE11A": "MRE11",
    "MTTP": "MT-TP",
    "PTRF": "CAVIN1",
    "PVRL1": "NECTIN1",
    "QARS": "EPRS",
    "RGAG1": "RTL9",
    "SLC6A5": "SLC6A2",
}

with transaction.atomic():
    old_pks = GenePanelSnapshot.objects.get_latest_ids(deleted=True).filter(
        panel__old_pk__in=missing_data.keys()
    )
    old_gps = GenePanelSnapshot.objects.filter(pk__in=old_pks).prefetch_related(
        "level4title"
    )
    print("Backing up the panels")
    for gps in old_gps:
        gps.increment_version()
        print("Backed up {}".format(gps))

    new_pks = GenePanelSnapshot.objects.get_latest_ids(deleted=True).filter(
        panel__old_pk__in=missing_data.keys()
    )
    new_gps = GenePanelSnapshot.objects.filter(pk__in=new_pks).prefetch_related(
        "level4title",
        "panel",
        "genepanelentrysnapshot_set",
        "genepanelentrysnapshot_set__evaluation",
        "genepanelentrysnapshot_set__evaluation__user",
    )

    for gps in new_gps:
        print("-" * 80)
        print(gps)
        old_pk = gps.panel.old_pk
        missing_panel_data = missing_data[old_pk]
        for original_gene_symbol in missing_panel_data.keys():
            gene_symbol = new_genes.get(original_gene_symbol, original_gene_symbol)

            try:
                gene = gps.get_gene(gene_symbol)
            except GenePanelEntrySnapshot.DoesNotExist:
                try:
                    gene = gps.get_gene(original_gene_symbol)
                except GenePanelEntrySnapshot.DoesNotExist:
                    print(
                        "[E] P:{0} G:{1: <12} or G:{1: <12} Does not exist".format(
                            old_pk, original_gene_symbol
                        )
                    )
                    continue

            missing_gene = missing_panel_data[original_gene_symbol]
            for evaluation in gene.evaluation.all().prefetch_related("user"):
                username = evaluation.user.username
                user_data = missing_gene.get(username)
                if user_data:
                    print(
                        "[U] P:{0} G:{1: <12}U:{2}".format(
                            old_pk, gene_symbol, evaluation.user.username
                        )
                    )
                    if evaluation.created != user_data["date"]:
                        if user_data["date"][-1] != "Z":
                            evaluation.created = user_data["date"] + "Z"
                        else:
                            evaluation.created = user_data["date"]
                    if not evaluation.version:
                        evaluation.version = user_data["version"]
                    evaluation.save()
