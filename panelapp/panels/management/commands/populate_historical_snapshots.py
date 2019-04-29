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

import djclick as click

from django.db import models
from django.db.models import Case
from django.db.models import Count
from django.db.models import When
from django.db.models import Value

from panels.models import GenePanelSnapshot
from panels.models import HistoricalSnapshot


@click.command()
def command():

    latest_panels = GenePanelSnapshot.objects.all().distinct("panel_id").order_by(
                "panel_id", "-major_version", "-minor_version", "-modified", "-pk"
            ).values_list("pk", flat=True)

    for gps in (
        GenePanelSnapshot.objects.all()
        .annotate(child_panels_count=Count("child_panels"))
        .annotate(
            is_super_panel=Case(
                When(child_panels_count__gt=0, then=Value(True)),
                default=Value(False),
                output_field=models.BooleanField(),
            )
        )
        .exclude(pk__in=latest_panels)
        .order_by("panel_id", "-major_version", "-minor_version")
        .iterator()
    ):
        HistoricalSnapshot().import_panel(panel=gps)
        gps.delete()
