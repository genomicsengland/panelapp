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
import os
from django.conf import settings
import requests
import re


class CellBaseConnector:
    def __init__(self, host=settings.CELL_BASE_CONNECTOR_REST):
        self.host = host
        self.url = None

    def create_url(self, version, species, category, subcategory, id, resource, excludes=None, includes=None):
        base_url = os.path.join(self.host, version, species, category, subcategory, id, resource)
        if excludes is not None:
            url = os.path.join(base_url, "?exclude=" + excludes)
            if includes is not None:
                url = os.path.join(url, "&include=" + includes)
        else:
            if includes is not None:
                url = os.path.join(base_url, "?include=" + includes)
            else:
                url = base_url

        self.url = url

    def execute(self):
        if self.url is not None:
            r = requests.get(self.url)
            response = r.json()
            for result in response["response"]:
                yield result["result"]

    def get_coding_transcripts_by_length(self, genes):
        self.create_url("latest", "hsapiens", "feature", "gene", ",".join(genes), "transcript",
                        includes="transcripts.id,transcripts.cdsLength,transcripts.biotype")
        for r in self.execute():
            yield r

    def get_transcripts(self, genes, coding=True):
        includes = ",".join([
            "transcripts.id",
            "transcripts.cdsLength",
            "transcripts.biotype",
            "transcripts.chromosome",
            "transcripts.strand",
            "transcripts.start",
            "transcripts.end"
        ])
        self.create_url("latest", "hsapiens", "feature", "gene", ",".join(genes), "transcript", includes=includes)
        all_transcripts = []
        for r in self.execute():
            if len(r) > 0:
                for trn in r:
                    for t in trn["transcripts"]:
                        if coding:
                            if t["biotype"] == "protein_coding":
                                all_transcripts.append(t)
                        else:
                            all_transcripts.append(t)
        return all_transcripts

    def get_exons(self, genes, coding=True):
        includes = ",".join([
            "transcripts.id",
            "transcripts.cdsLength",
            "transcripts.biotype",
            "transcripts.chromosome",
            "transcripts.start",
            "transcripts.end",
            "transcripts.exons"
        ])
        self.create_url("latest", "hsapiens", "feature", "gene", ",".join(genes), "transcript", includes=includes)
        all_exons = []
        for r in self.execute():
            if len(r) > 0:
                for trn in r:
                    for t in trn["transcripts"]:
                        if coding:
                            if t["biotype"] == "protein_coding":
                                for exon in t["exons"]:
                                    all_exons.append(exon)

                        else:
                            for exon in t["exons"]:
                                    all_exons.append(exon)

        return all_exons

    def get_gene(self, genes, coding=True):
        self.create_url("latest", "hsapiens", "feature", "gene", ",".join(genes), "info",
                        excludes="transcripts,expressionValues,_chunkIds")
        all_genes = []
        for r in self.execute():
            if len(r) > 0:
                for gene in r:
                    if coding:
                        if gene["biotype"] == "protein_coding":
                            all_genes.append(gene)
                    else:
                        all_genes.append(gene)

        return all_genes


def remove_non_ascii(text, replacemenet=' '):
    return re.sub(r'[^\x00-\x7F]+', ' ', text)
