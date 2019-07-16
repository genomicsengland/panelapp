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
from django.db import transaction

from panels.models import GenePanelSnapshot


@click.command()
def command():
    for panel in GenePanelSnapshot.objects.get_active_annotated(
        all=True, internal=True, superpanels=False
    ).filter(is_child_panel=True):
        with transaction.atomic():
            new_panel = panel.increment_version(include_superpanels=False)
            new_panel._update_saved_stats(update_superpanels=False)

    click.echo('Updated all simple panels')

    for super_panel in GenePanelSnapshot.objects.get_active_annotated(
        all=True, internal=True, superpanels=True
    ).filter(is_super_panel=True):
        with transaction.atomic():
            new_super_panel = super_panel.increment_version()
            new_super_panel._update_saved_stats(update_superpanels=False)

    click.echo('Updated all super panels')
