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
from django.contrib.postgres.fields import ArrayField


class Level4Title(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    level3title = models.CharField(max_length=255)
    level2title = models.CharField(max_length=255)
    omim = ArrayField(models.CharField(max_length=255))
    orphanet = ArrayField(models.CharField(max_length=255))
    hpo = ArrayField(models.CharField(max_length=255))

    def __str__(self):
        return str(self.name)

    def __eq__(self, other):
        if other == self.name:
            return True
        else:
            return False

    def dict_tr(self):
        return {
            "name": self.name,
            "description": self.description,
            "level3title": self.level3title,
            "level2title": self.level2title,
            "omim": self.omim,
            "orphanet": self.orphanet,
            "hpo": self.hpo,
        }
