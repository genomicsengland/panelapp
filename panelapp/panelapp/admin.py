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
from django.contrib import admin
from django.contrib.sites.models import Site
from markdownx.admin import MarkdownxModelAdmin
from .models import HomeText
from .models import Image
from .models import File


admin.site.site_header = "PanelApp administration"


class HomeTextAdmin(MarkdownxModelAdmin):
    list_display = ("section", "href", "title")


class ImageAdmin(admin.ModelAdmin):
    list_display = ("pk", "alt", "title")
    readonly_fields = ("view_example",)

    def view_example(self, obj):
        "Example of how to use this image with markdown syntax"

        return "![{0}]({1})".format(obj.alt, obj.image.url)

    view_example.empty_value_display = ""
    view_example.short_description = "Markdown example"


class FileAdmin(admin.ModelAdmin):
    list_display = ("pk", "title")
    readonly_fields = ("view_example",)

    def view_example(self, obj):
        "File url"

        return "[{0}]({1})".format(obj.title, obj.file.url)

    view_example.empty_value_display = ""
    view_example.short_description = "File url"


admin.site.register(HomeText, HomeTextAdmin)
admin.site.register(Image, ImageAdmin)
admin.site.register(File, FileAdmin)
