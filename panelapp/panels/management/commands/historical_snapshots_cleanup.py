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

from django.core.paginator import Paginator
from django.db.models import Count, Q

import djclick as click

from panels.models import Evaluation
from panels.models import Evidence
from panels.models import TrackRecord
from panels.models import Comment


@click.command()
def command():
    """Goes through the database and clears any Evidence, TrackRecord, Evaluation, Comment which were in ManyToMany
    rel and aren't linked to any other models.

    Since some tables are quite large (TrackRecord for example), it's best to run this script in a
    background after the `populate_historical_snapshots`.
    """

    for model_type in [Evidence, TrackRecord, Evaluation, Comment]:
        qs = model_type.objects\
            .annotate(g_count=Count('genepanelentrysnapshot'), s_count=Count('str'), r_count=Count('region'))\
            .exclude(Q(g_count__gt=0) | Q(s_count__gt=0) | Q(r_count__gt=0))

        if model_type == Comment:
            qs = qs.annotate(e_count=Count('evaluation')).exclude(e_count__gt=0)

        items = qs.order_by('pk').values_list('pk', flat=True)
        items_pks = list(items)

        total = 0
        for page in chunked_iterator(items_pks):
            model_type.objects.filter(pk__in=page).only('pk').delete()
            total = total + len(page)
            click.echo('{} Deleted: {}'.format(model_type, len(page)))


def chunked_iterator(queryset, chunk_size=50000):
    paginator = Paginator(queryset, chunk_size)
    for page in range(1, paginator.num_pages + 1):
        yield paginator.page(page).object_list
