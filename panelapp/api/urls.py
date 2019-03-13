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
from django.urls import path, include
from django.conf import settings
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from .permissions import ReadOnlyPermissions

schema_view = get_schema_view(
    openapi.Info(
        title="PanelApp API",
        default_version=settings.REST_FRAMEWORK['DEFAULT_VERSION'],
        description="PanelApp API",
        terms_of_service="https://panelapp.genomicsengland.co.uk/policies/terms/",
        contact=openapi.Contact(email="panelapp@genomicsengland.co.uk"),
        license=openapi.License(name="MIT License"),
    ),
    patterns=['api', ],
    validators=['flex', 'ssv'],
    public=True,
    permission_classes=(ReadOnlyPermissions, ),
)

app_name = 'api'
urlpatterns = [
    path('v1/', include('api.v1.urls', namespace='v1')),
]
