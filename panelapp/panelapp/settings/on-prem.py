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
from .base import *  # noqa

##############################################################################
# This profile is for backward compatibility only.
# To deploy the application on-premise, using RabbitMQ and local file-system.
##############################################################################
#
# It expects the following environment variables:
#
# Secrets
#
# * `SECRET_KEY` - used to encrypt cookies
# * `DATABASE_URL` - PostgreSQL config url in the following format: postgresql://username:password@host:port/database_name
# * `CELERY_BROKER_URL` - Celery config for RabbitMQ, in the following format: amqp://username:password@host:port/virtual
# * `HEALTH_CHECK_TOKEN` - URL token for authorizing status checks
# * `EMAIL_HOST_PASSWORD` - SMTP password
# * `ALLOWED_HOSTS` - whitelisted hostnames, if user tries to access website which isn't here Django will throw 500 error
# * `DJANGO_ADMIN_URL` - change admin URL to something secure.
#
# Not Secrets
#
# * `DEFAULT_FROM_EMAIL` - we send emails as this address
# * `PANEL_APP_EMAIL` - PanelApp email address
# * `DJANGO_LOG_LEVEL` - by default set to INFO, other options: DEBUG, ERROR
# * `STATIC_ROOT` - location for static files which are collected with `python manage.py collectstatic --noinput`
# * `MEDIA_ROOT` - location for user uploaded files
# * `EMAIL_HOST` - SMTP host
# * `EMAIL_HOST_USER` - SMTP username
# * `EMAIL_PORT` - SMTP server port
# * `EMAIL_USE_TLS` - Set to True (default) if SMTP server uses TLS
