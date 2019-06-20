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
from django.db import models
from model_utils.models import TimeStampedModel
from accounts.models import User


class Comment(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.PROTECT, null=True)
    comment = models.TextField()
    flagged = models.BooleanField(default=False)
    last_updated = models.DateTimeField(null=True, blank=True)
    version = models.CharField(null=True, blank=True, max_length=255)

    class Meta:
        ordering = ["-created"]

    def dict_tr(self):
        return {"date": self.created, "comment": self.comment}

    def __str__(self):
        return "{}: {}".format(self.user.get_full_name(), self.comment[:30])

    def __eq__(self, other):
        if self.comment == other.comment:
            return True
        else:
            return False
