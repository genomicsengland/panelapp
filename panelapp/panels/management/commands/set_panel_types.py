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
import djclick as click
from django.db import transaction
from panels.models import GenePanel
from panels.models import PanelType


@click.command()
@click.argument("csv_file", type=click.Path(exists=True))
def command(csv_file):
    panel_types = {t.slug: t for t in PanelType.objects.all()}
    gene_panels = {
        str(p.pk): p for p in GenePanel.objects.all().prefetch_related("types")
    }

    with open(click.format_filename(csv_file), "r") as f:
        reader = csv.reader(f)
        next(reader)  # skip header

        with transaction.atomic():
            error_lines = []

            for index, line in enumerate(reader):
                if line and len(line) == 2:
                    panel_id, slug = line
                    panel = gene_panels.get(panel_id, None)
                    panel_type = panel_types.get(slug, None)

                    if not panel or not panel_type:
                        if not panel:
                            click.secho(
                                "[{}] Cant find panel with id: {}".format(
                                    index + 1, panel_id
                                ),
                                err=True,
                                fg="red",
                            )
                        if not panel_type:
                            click.secho(
                                "[{}] Cant find panel_type with slug: {}".format(
                                    index + 1, slug
                                ),
                                err=True,
                                fg="red",
                            )
                        error_lines.append([index, panel_id, slug])
                        continue

                    panel.types.add(panel_type)  # it won't duplicate

                else:
                    click.secho(
                        "[{}] Skipping line, incorrect format".format(index + 1)
                    )

            if error_lines:
                click.secho("Couldn't assign {} records".format(len(error_lines)))
            else:
                click.secho("All done", fg="green")
