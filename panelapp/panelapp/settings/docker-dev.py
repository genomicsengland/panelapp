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

# Profile used for local, dockerised development

from .base import *  # noqa

DEBUG = True

RUNSERVERPLUS_SERVER_ADDRESS_PORT = "0.0.0.0:8000"

INSTALLED_APPS += ("debug_toolbar", "django_extensions")  # noqa

MIDDLEWARE += ("debug_toolbar.middleware.DebugToolbarMiddleware",)  # noqa

INTERNAL_IPS = ["127.0.0.1"]

EMAIL_HOST = "localhost"
EMAIL_PORT = 25
EMAIL_HOST_USER = None
EMAIL_HOST_PASSWORD = None

ALLOWED_HOSTS = ALLOWED_HOSTS + ["localhost", "*"]

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

CELERY_TASK_PUBLISH_RETRY_POLICY = {
    "max_retries": 3,
    "interval_start": 0,
    "interval_step": 0.2,
    "interval_max": 0.2,
}
