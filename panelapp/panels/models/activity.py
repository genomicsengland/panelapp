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
from copy import deepcopy
from django.db import models
from django.db.models import Q
from django.core.serializers.json import DjangoJSONEncoder
from django.contrib.postgres.fields import JSONField
from model_utils.models import TimeStampedModel

from accounts.models import User
from .genepanel import GenePanel


class ActivityManager(models.Manager):
    def visible_to_public(self):
        """Return activities for all publicly visible panels"""

        qs = self.get_queryset()
        qs = qs.filter(
            Q(panel__status=GenePanel.STATUS.public)
            | Q(panel__status=GenePanel.STATUS.promoted)
        )
        return qs

    def visible_to_gel(self):
        """Return activities visible to GeL curators"""

        return self.get_queryset()


class Activity(TimeStampedModel):
    class Meta:
        ordering = ("-created",)

    objects = ActivityManager()

    panel = models.ForeignKey(GenePanel, on_delete=models.SET_NULL, null=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    text = models.TextField()
    item_type = models.CharField(max_length=32, null=True)  # TODO (Oleg) change to Enum
    entity_type = models.CharField(max_length=32, null=True)
    entity_name = models.CharField(max_length=128, null=True)
    extra_data = JSONField(default=dict, encoder=DjangoJSONEncoder)

    @property
    def panel_version(self):
        return self.extra_data.get("panel_version")

    @property
    def panel_name(self):
        return self.extra_data.get("panel_name")

    @property
    def user_name(self):
        return self.extra_data.get("user_name")

    @classmethod
    def log(cls, user, panel_snapshot, text, extra_info):
        extra_data = deepcopy(extra_info)

        if user:
            extra_data["user_name"] = user.get_full_name()

        extra_data["panel_name"] = panel_snapshot.panel.name
        extra_data["panel_id"] = panel_snapshot.panel_id
        extra_data["panel_version"] = panel_snapshot.version

        if "entity_type" in extra_info:
            extra_data["item_type"] = "entity"
            extra_data["entity_type"] = extra_info["entity_type"]
            extra_data["entity_name"] = extra_info["entity_name"]
        else:
            extra_data["item_type"] = "panel"

        cls.objects.create(
            user=user,
            panel=panel_snapshot.panel,
            text=text,
            extra_data=extra_data,
            item_type=extra_data["item_type"],
            entity_type=extra_data.get("entity_type"),
            entity_name=extra_data.get("entity_name"),
        )
