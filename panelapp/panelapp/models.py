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
"""
Author: Oleg Gerasimenko, 2017

Models here are used to render text on the homepage. This info can be edited
in the admin panel.

@MIGRATION When we migrate from v1 to v2 we need to add `alt` and `title` to the images
@MIGRATION HomeText data should be prefield via django migration, and populated with the migrate script
"""

from django.db import models
import markdown
from markdownx.models import MarkdownxField
from panelapp.utils.storage import OverwriteStorage


class HomeText(models.Model):
    section = models.IntegerField()
    title = models.CharField(max_length=64)
    href = models.CharField(max_length=64, unique=True)
    text = MarkdownxField(blank=True)

    class Meta:
        ordering = ["section"]

    def __str__(self):
        return self.title

    @property
    def render_markdown(self):
        md = markdown.Markdown()
        return md.convert(self.text)


class Image(models.Model):
    image = models.ImageField(
        upload_to="images", max_length=255
    )
    alt = models.CharField("Alterative text", max_length=64)
    title = models.CharField("Image title", max_length=128, null=True, blank=True)

    def __str__(self):
        return self.alt


class File(models.Model):
    """File storage for any file which should be available online"""

    file = models.FileField(
        upload_to="files", max_length=512
    )
    title = models.CharField("File title", max_length=128)

    def __str__(self):
        return self.title
