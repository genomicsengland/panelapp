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
from django.conf.urls import url
from django.views.generic.base import RedirectView
from django.urls import reverse_lazy

from .views import RedirectGeneView
from .views import RedirectPanelView
from .views import RedirectWebServices
from .views import RedirectGenePanelView

app_name = "v1rewrites"
urlpatterns = [
    url(r"^$", RedirectView.as_view(url="/", permanent=True)),
    url(r"^PanelApp/$", RedirectView.as_view(url="/", permanent=True)),
    url(r"^PanelApp/Login$", RedirectView.as_view(url="/", permanent=True)),
    url(
        r"^PanelApp/Genes$", RedirectView.as_view(url="/panels/genes/", permanent=True)
    ),
    url(
        r"^PanelApp/Genes/(?P<gene_symbol>.*)$",
        RedirectGeneView.as_view(permanent=True),
    ),
    url(
        r"^PanelApp/PanelBrowser$",
        RedirectView.as_view(url=reverse_lazy("panels:index"), permanent=True),
    ),
    url(
        r"^PanelApp/EditPanel/(?P<old_pk>[a-z0-9]+)$",
        RedirectPanelView.as_view(permanent=True),
    ),
    url(
        r"^PanelApp/GeneReview/(?P<old_pk>[a-z0-9]+)/(?P<gene_symbol>.*)$",
        RedirectGenePanelView.as_view(permanent=True),
    ),
    url(r"^WebServices/(?P<ws>.*)$", RedirectWebServices.as_view(permanent=True)),
]
