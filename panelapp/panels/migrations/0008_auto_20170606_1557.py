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
# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2017-06-06 14:57
from __future__ import unicode_literals

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("panels", "0007_auto_20170531_1122")]

    operations = [
        migrations.AlterModelOptions(
            name="genepanelentrysnapshot",
            options={
                "get_latest_by": "created",
                "ordering": ["-saved_gel_status", "-created"],
            },
        ),
        migrations.RemoveField(model_name="evaluation", name="transcript"),
        migrations.AlterField(
            model_name="activity",
            name="gene_symbol",
            field=models.CharField(max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name="evaluation",
            name="phenotypes",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.CharField(max_length=255, null=True),
                blank=True,
                null=True,
                size=None,
            ),
        ),
        migrations.AlterField(
            model_name="evaluation",
            name="publications",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.CharField(max_length=255, null=True),
                blank=True,
                null=True,
                size=None,
            ),
        ),
        migrations.AlterField(
            model_name="evaluation",
            name="rating",
            field=models.CharField(
                blank=True,
                choices=[
                    ("GREEN", "Green List (high evidence)"),
                    ("RED", "Red List (low evidence)"),
                    ("AMBER", "I don't know"),
                ],
                max_length=255,
            ),
        ),
        migrations.AlterField(
            model_name="trackrecord",
            name="issue_type",
            field=models.CharField(
                choices=[
                    ("Created", "Created"),
                    ("NewSource", "Added New Source"),
                    ("ChangedGeneName", "Changed Gene Name"),
                    ("SetPhenotypes", "Set Phenotypes"),
                    ("SetModelofInheritance", "Set Model of Inheritance"),
                    ("ClearSources", "Clear Sources"),
                ],
                max_length=255,
            ),
        ),
    ]
