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
from django.views.generic.base import RedirectView
from django.urls import reverse_lazy
from panels.models import GenePanel


class V1RedirectMixin(RedirectView):
    url = "/?v2"

    def dispatch(self, request, *args, **kwargs):
        self.check()

        if request.GET:
            self.url = "{}?{}".format(self.url, request.GET.urlencode())

        return super().dispatch(request, *args, **kwargs)


class RedirectGeneView(V1RedirectMixin):
    """Redirect to the list of panels for a specific gene"""

    def check(self):
        self.url = reverse_lazy(
            "panels:entity_detail", args=(self.kwargs["gene_symbol"],)
        )


class RedirectPanelView(V1RedirectMixin):
    """Check if we have an id for the old panel and redirect to the new id"""

    def check(self):
        try:
            gp = GenePanel.objects.get(old_pk=self.kwargs.get("old_pk"))
            self.url = reverse_lazy("panels:detail", args=(gp.pk,))
        except GenePanel.DoesNotExist:
            self.url = "/panels/"


class RedirectGenePanelView(V1RedirectMixin):
    """Redirect to a gene in a panel"""

    def check(self):
        try:
            gp = GenePanel.objects.get(old_pk=self.kwargs.get("old_pk"))
            self.url = reverse_lazy(
                "panels:evaluation",
                args=(gp.pk, "gene", self.kwargs.get("gene_symbol")),
            )
        except GenePanel.DoesNotExist:
            self.url = "/panels/"


class RedirectWebServices(V1RedirectMixin):
    """Redirect webservices"""

    def check(self):
        self.url = "/WebServices/{}".format(self.kwargs["ws"])
