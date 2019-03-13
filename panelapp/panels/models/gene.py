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
from datetime import datetime
from django.core.exceptions import ValidationError
from django.db import models
from django.contrib.postgres.fields import JSONField, ArrayField


class Gene(models.Model):
    gene_symbol = models.CharField(max_length=255, primary_key=True, db_index=True)
    gene_name = models.CharField(max_length=255, null=True)
    ensembl_genes = JSONField()
    omim_gene = ArrayField(models.CharField(max_length=255), null=True)
    alias = ArrayField(models.CharField(max_length=255), null=True)
    biotype = models.CharField(max_length=255, null=True)
    alias_name = ArrayField(models.CharField(max_length=255), null=True)
    hgnc_symbol = models.CharField(max_length=255, null=True)
    hgnc_date_symbol_changed = models.DateField(null=True)
    hgnc_release = models.DateField(null=True)
    hgnc_id = models.CharField(max_length=255, null=True)
    active = models.BooleanField(default=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=[
                'gene_symbol',
                'active'
            ]),
        ]

    def __str__(self):
        return "{symbol} (HGNC:  {hgnc_symbol}), {gene_name}".format(
            symbol=self.gene_symbol,
            hgnc_symbol=self.hgnc_symbol,
            gene_name=self.gene_name
        )

    def dict_tr(self):
        return {
            'gene_symbol': self.gene_symbol,
            'gene_name': self.gene_name,
            'ensembl_genes': self.ensembl_genes,
            'omim_gene': self.omim_gene,
            'alias': self.alias,
            'biotype': self.biotype,
            'alias_name': self.alias_name,
            'hgnc_symbol': self.hgnc_symbol,
            'hgnc_date_symbol_changed': self.hgnc_date_symbol_changed,
            'hgnc_release': self.hgnc_release,
            'hgnc_id': self.hgnc_id
        }

    def clean_import_dates(self, record):
        try:
            self.full_clean()
        except ValidationError as err:
            if 'hgnc_date_symbol_changed' in err.error_dict:
                val = record.get('hgnc_date_symbol_changed', None)
                if val:
                    try:
                        converted_val = datetime.strptime(val, '%d-%m-%y')
                    except ValueError:
                        converted_val = datetime.strptime(val, '%d/%m/%y')
                    self.hgnc_date_symbol_changed = converted_val

            if 'hgnc_release' in err.error_dict:
                val = record.get('hgnc_release', None)
                if val:
                    try:
                        converted_val = datetime.strptime(val, '%d-%m-%y')
                    except ValueError:
                        converted_val = datetime.strptime(val, '%d/%m/%y')
                    self.hgnc_release = converted_val

    @classmethod
    def from_dict(cls, dictionary: dict):

        instance = cls(
            gene_name=dictionary.get('gene_name', None),
            gene_symbol=dictionary['gene_symbol'],
            ensembl_genes=dictionary.get('ensembl_genes', {}),
            omim_gene=dictionary.get('omim_gene', []),
            alias=dictionary.get('alias', []),
            biotype=dictionary.get('biotype', 'unknown'),
            alias_name=dictionary.get('alias_name', []),
            hgnc_symbol=dictionary['hgnc_symbol'],
            hgnc_release=dictionary.get('hgnc_release', None),
            hgnc_id=dictionary.get('hgnc_id', None),
            hgnc_date_symbol_changed=dictionary.get('hgnc_date_symbol_changed', None)
        )

        instance.clean_import_dates(dictionary)

        return instance
