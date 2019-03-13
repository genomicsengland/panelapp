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
import csv
from datetime import datetime
from django.http import StreamingHttpResponse
from django.views import View
from panels.models import GenePanelSnapshot
from .entities import EchoWriter
from panelapp.mixins import GELReviewerRequiredMixin


class DownloadAllRegions(GELReviewerRequiredMixin, View):
    def regions_iterator(self):
        yield (
            "Name",
            "Verbose Name",
            "Chromosome",
            "Position GRCh37 start",
            "Position GRCh37 end",
            "Position GRCh38 start",
            "Position GRCh38 end",
            "Haploinsufficiency Score",
            "Triplosensitivity Score",
            "Required region overlap",
            "Variant types",
            "Symbol",
            "Panel Id",
            "Panel Name",
            "Panel Version",
            "Panel Status",
            "List",
            "Sources",
            "Mode of inheritance",
            "Tags",
            "EnsemblId(GRch37)",
            "EnsemblId(GRch38)",
            "Biotype",
            "Phenotypes",
            "GeneLocation(GRch37)",
            "GeneLocation(GRch38)",
            "Panel Types",
            "Super Panel Id",
            "Super Panel Name",
            "Super Panel Version",
        )

        for gps in GenePanelSnapshot.objects.get_active(
            all=True, internal=True
        ).iterator():
            is_super_panel = gps.is_super_panel
            super_panel_id = gps.panel_id
            super_panel_name = gps.level4title.name
            super_panel_version = gps.version

            for entry in gps.get_all_regions_extra:
                color = entry.entity_color_name

                if isinstance(entry.phenotypes, list):
                    phenotypes = ";".join(entry.phenotypes)
                else:
                    phenotypes = ""

                row = [
                    entry.name,
                    entry.verbose_name,
                    entry.chromosome,
                    entry.position_37.lower if entry.position_37 else "",
                    entry.position_37.upper if entry.position_37 else "",
                    entry.position_38.lower,
                    entry.position_38.upper,
                    entry.haploinsufficiency_score
                    if entry.haploinsufficiency_score
                    else "",
                    entry.triplosensitivity_score
                    if entry.triplosensitivity_score
                    else "",
                    entry.required_overlap_percentage,
                    entry.type_of_variants,
                    entry.gene.get("gene_symbol") if entry.gene else "",
                    gps.panel.pk,
                    gps.level4title.name,
                    gps.version,
                    str(gps.panel.status).upper(),
                    color,
                    ";".join([evidence.name for evidence in entry.evidence.all()]),
                    entry.moi,
                    ";".join([tag.name for tag in entry.tags.all()]),
                    entry.gene.get("ensembl_genes", {})
                    .get("GRch37", {})
                    .get("82", {})
                    .get("ensembl_id", "")
                    if entry.gene
                    else "",
                    entry.gene.get("ensembl_genes", {})
                    .get("GRch38", {})
                    .get("90", {})
                    .get("ensembl_id", "")
                    if entry.gene
                    else "",
                    entry.gene.get("biotype", "-") if entry.gene else "-",
                    phenotypes,
                    entry.gene.get("ensembl_genes", {})
                    .get("GRch37", {})
                    .get("82", {})
                    .get("location", "")
                    if entry.gene
                    else "",
                    entry.gene.get("ensembl_genes", {})
                    .get("GRch38", {})
                    .get("90", {})
                    .get("location", "")
                    if entry.gene
                    else "",
                    ";".join([t.name for t in entry.panel.panel.types.all()]),
                    super_panel_id if is_super_panel else "-",
                    super_panel_name if is_super_panel else "-",
                    super_panel_version if is_super_panel else "-",
                ]
                yield row

    def get(self, request, *args, **kwargs):
        pseudo_buffer = EchoWriter()
        writer = csv.writer(pseudo_buffer, delimiter="\t")

        response = StreamingHttpResponse(
            (writer.writerow(row) for row in self.regions_iterator()),
            content_type="text/tab-separated-values",
        )
        attachment = "attachment; filename=All_regions_{}.tsv".format(
            datetime.now().strftime("%Y%m%d-%H%M")
        )
        response["Content-Disposition"] = attachment
        return response
