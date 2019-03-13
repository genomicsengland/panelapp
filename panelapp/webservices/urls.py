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
from rest_framework.urlpatterns import format_suffix_patterns
from . import views

# Wire up our API using automatic URL routing.
# Additionally, we include login URLs for the browsable API.
app_name = 'webservices'
urlpatterns = [
    url(r'^get_panel/(.+)/', views.get_panel, name="get_panel"),
    url(r'^search_genes/(.+)/', views.search_by_gene, name="search_genes"),
    url(r'^list_panels/', views.list_panels, name="list_panels"),
    url(r'^list_entities/', views.list_entities, name="list_entities"),
]

urlpatterns = format_suffix_patterns(urlpatterns)
