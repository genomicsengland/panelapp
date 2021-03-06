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
# Generated by Django 2.0.6 on 2018-06-15 10:47

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [("panels", "0051_auto_20180608_1024")]

    operations = [
        migrations.AlterField(
            model_name="comment",
            name="user",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="evaluation",
            name="mode_of_pathogenicity",
            field=models.CharField(
                blank=True,
                choices=[
                    ("", "Provide exceptions to loss-of-function"),
                    (
                        "Loss-of-function variants (as defined in pop up message) DO NOT cause this phenotype - please provide details in the comments",
                        "Loss-of-function variants (as defined in pop up message) DO NOT cause this phenotype - please provide details in the comments",
                    ),
                    ("Other", "Other - please provide details in the comments"),
                ],
                max_length=255,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="evaluation",
            name="moi",
            field=models.CharField(
                blank=True,
                choices=[
                    ("", "Provide a mode of inheritance"),
                    (
                        "MONOALLELIC, autosomal or pseudoautosomal, NOT imprinted",
                        "MONOALLELIC, autosomal or pseudoautosomal, NOT imprinted",
                    ),
                    (
                        "MONOALLELIC, autosomal or pseudoautosomal, maternally imprinted (paternal allele expressed)",
                        "MONOALLELIC, autosomal or pseudoautosomal, maternally imprinted (paternal allele expressed)",
                    ),
                    (
                        "MONOALLELIC, autosomal or pseudoautosomal, paternally imprinted (maternal allele expressed)",
                        "MONOALLELIC, autosomal or pseudoautosomal, paternally imprinted (maternal allele expressed)",
                    ),
                    (
                        "MONOALLELIC, autosomal or pseudoautosomal, imprinted status unknown",
                        "MONOALLELIC, autosomal or pseudoautosomal, imprinted status unknown",
                    ),
                    (
                        "BIALLELIC, autosomal or pseudoautosomal",
                        "BIALLELIC, autosomal or pseudoautosomal",
                    ),
                    (
                        "BOTH monoallelic and biallelic, autosomal or pseudoautosomal",
                        "BOTH monoallelic and biallelic, autosomal or pseudoautosomal",
                    ),
                    (
                        "BOTH monoallelic and biallelic (but BIALLELIC mutations cause a more SEVERE disease form), autosomal or pseudoautosomal",
                        "BOTH monoallelic and biallelic (but BIALLELIC mutations cause a more SEVERE disease form), autosomal or pseudoautosomal",
                    ),
                    (
                        "X-LINKED: hemizygous mutation in males, biallelic mutations in females",
                        "X-LINKED: hemizygous mutation in males, biallelic mutations in females",
                    ),
                    (
                        "X-LINKED: hemizygous mutation in males, monoallelic mutations in females may cause disease (may be less severe, later onset than males)",
                        "X-LINKED: hemizygous mutation in males, monoallelic mutations in females may cause disease (may be less severe, later onset than males)",
                    ),
                    ("MITOCHONDRIAL", "MITOCHONDRIAL"),
                    ("Unknown", "Unknown"),
                    ("Other", "Other - please specifiy in evaluation comments"),
                ],
                max_length=255,
                null=True,
                verbose_name="Mode of Inheritance",
            ),
        ),
        migrations.AlterField(
            model_name="evaluation",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL
            ),
        ),
        migrations.AlterField(
            model_name="evidence",
            name="reviewer",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to="accounts.Reviewer",
            ),
        ),
        migrations.AlterField(
            model_name="genepanelentrysnapshot",
            name="gene_core",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT, to="panels.Gene"
            ),
        ),
        migrations.AlterField(
            model_name="genepanelentrysnapshot",
            name="mode_of_pathogenicity",
            field=models.CharField(
                blank=True,
                choices=[
                    ("", "Provide exceptions to loss-of-function"),
                    (
                        "Loss-of-function variants (as defined in pop up message) DO NOT cause this phenotype - please provide details in the comments",
                        "Loss-of-function variants (as defined in pop up message) DO NOT cause this phenotype - please provide details in the comments",
                    ),
                    ("Other", "Other - please provide details in the comments"),
                ],
                max_length=255,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="genepanelentrysnapshot",
            name="moi",
            field=models.CharField(
                choices=[
                    ("", "Provide a mode of inheritance"),
                    (
                        "MONOALLELIC, autosomal or pseudoautosomal, NOT imprinted",
                        "MONOALLELIC, autosomal or pseudoautosomal, NOT imprinted",
                    ),
                    (
                        "MONOALLELIC, autosomal or pseudoautosomal, maternally imprinted (paternal allele expressed)",
                        "MONOALLELIC, autosomal or pseudoautosomal, maternally imprinted (paternal allele expressed)",
                    ),
                    (
                        "MONOALLELIC, autosomal or pseudoautosomal, paternally imprinted (maternal allele expressed)",
                        "MONOALLELIC, autosomal or pseudoautosomal, paternally imprinted (maternal allele expressed)",
                    ),
                    (
                        "MONOALLELIC, autosomal or pseudoautosomal, imprinted status unknown",
                        "MONOALLELIC, autosomal or pseudoautosomal, imprinted status unknown",
                    ),
                    (
                        "BIALLELIC, autosomal or pseudoautosomal",
                        "BIALLELIC, autosomal or pseudoautosomal",
                    ),
                    (
                        "BOTH monoallelic and biallelic, autosomal or pseudoautosomal",
                        "BOTH monoallelic and biallelic, autosomal or pseudoautosomal",
                    ),
                    (
                        "BOTH monoallelic and biallelic (but BIALLELIC mutations cause a more SEVERE disease form), autosomal or pseudoautosomal",
                        "BOTH monoallelic and biallelic (but BIALLELIC mutations cause a more SEVERE disease form), autosomal or pseudoautosomal",
                    ),
                    (
                        "X-LINKED: hemizygous mutation in males, biallelic mutations in females",
                        "X-LINKED: hemizygous mutation in males, biallelic mutations in females",
                    ),
                    (
                        "X-LINKED: hemizygous mutation in males, monoallelic mutations in females may cause disease (may be less severe, later onset than males)",
                        "X-LINKED: hemizygous mutation in males, monoallelic mutations in females may cause disease (may be less severe, later onset than males)",
                    ),
                    ("MITOCHONDRIAL", "MITOCHONDRIAL"),
                    ("Unknown", "Unknown"),
                    ("Other", "Other - please specifiy in evaluation comments"),
                ],
                max_length=255,
                verbose_name="Mode of inheritance",
            ),
        ),
        migrations.AlterField(
            model_name="genepanelentrysnapshot",
            name="panel",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                to="panels.GenePanelSnapshot",
            ),
        ),
        migrations.AlterField(
            model_name="genepanelsnapshot",
            name="level4title",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT, to="panels.Level4Title"
            ),
        ),
        migrations.AlterField(
            model_name="genepanelsnapshot",
            name="panel",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT, to="panels.GenePanel"
            ),
        ),
        migrations.AlterField(
            model_name="str",
            name="gene_core",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to="panels.Gene",
            ),
        ),
        migrations.AlterField(
            model_name="str",
            name="mode_of_pathogenicity",
            field=models.CharField(
                blank=True,
                choices=[
                    ("", "Provide exceptions to loss-of-function"),
                    (
                        "Loss-of-function variants (as defined in pop up message) DO NOT cause this phenotype - please provide details in the comments",
                        "Loss-of-function variants (as defined in pop up message) DO NOT cause this phenotype - please provide details in the comments",
                    ),
                    ("Other", "Other - please provide details in the comments"),
                ],
                max_length=255,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="str",
            name="moi",
            field=models.CharField(
                choices=[
                    ("", "Provide a mode of inheritance"),
                    (
                        "MONOALLELIC, autosomal or pseudoautosomal, NOT imprinted",
                        "MONOALLELIC, autosomal or pseudoautosomal, NOT imprinted",
                    ),
                    (
                        "MONOALLELIC, autosomal or pseudoautosomal, maternally imprinted (paternal allele expressed)",
                        "MONOALLELIC, autosomal or pseudoautosomal, maternally imprinted (paternal allele expressed)",
                    ),
                    (
                        "MONOALLELIC, autosomal or pseudoautosomal, paternally imprinted (maternal allele expressed)",
                        "MONOALLELIC, autosomal or pseudoautosomal, paternally imprinted (maternal allele expressed)",
                    ),
                    (
                        "MONOALLELIC, autosomal or pseudoautosomal, imprinted status unknown",
                        "MONOALLELIC, autosomal or pseudoautosomal, imprinted status unknown",
                    ),
                    (
                        "BIALLELIC, autosomal or pseudoautosomal",
                        "BIALLELIC, autosomal or pseudoautosomal",
                    ),
                    (
                        "BOTH monoallelic and biallelic, autosomal or pseudoautosomal",
                        "BOTH monoallelic and biallelic, autosomal or pseudoautosomal",
                    ),
                    (
                        "BOTH monoallelic and biallelic (but BIALLELIC mutations cause a more SEVERE disease form), autosomal or pseudoautosomal",
                        "BOTH monoallelic and biallelic (but BIALLELIC mutations cause a more SEVERE disease form), autosomal or pseudoautosomal",
                    ),
                    (
                        "X-LINKED: hemizygous mutation in males, biallelic mutations in females",
                        "X-LINKED: hemizygous mutation in males, biallelic mutations in females",
                    ),
                    (
                        "X-LINKED: hemizygous mutation in males, monoallelic mutations in females may cause disease (may be less severe, later onset than males)",
                        "X-LINKED: hemizygous mutation in males, monoallelic mutations in females may cause disease (may be less severe, later onset than males)",
                    ),
                    ("MITOCHONDRIAL", "MITOCHONDRIAL"),
                    ("Unknown", "Unknown"),
                    ("Other", "Other - please specifiy in evaluation comments"),
                ],
                max_length=255,
                verbose_name="Mode of inheritance",
            ),
        ),
        migrations.AlterField(
            model_name="str",
            name="panel",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                to="panels.GenePanelSnapshot",
            ),
        ),
        migrations.AlterField(
            model_name="trackrecord",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL
            ),
        ),
    ]
