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
import os
import logging
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.views.generic import View
from django.views.generic import ListView
from django.http import JsonResponse
from django.core import mail
from celery.task.control import inspect
from kombu import Connection
from .models import HomeText


class Homepage(ListView):
    model = HomeText


class HealthCheckView(View):
    def get(self, request, *args, **kwargs):
        token = (
            request.META.get("TOKEN")
            if request.META.get("TOKEN")
            else request.GET.get("token")
        )

        if (
            not settings.HEALTH_CHECK_TOKEN
            or not token
            or token != settings.HEALTH_CHECK_TOKEN
        ):
            raise PermissionDenied

        out = {}
        status = 200

        for service in settings.HEALTH_CHECK_SERVICES:
            service_method = getattr(self, "_check_{service}".format(service=service))
            if callable(service_method):
                out[service] = service_method()
                if out[service] != "OK":
                    status = 500

        return JsonResponse(out, status=status)

    @staticmethod
    def _check_maintenance():
        status = "OK"
        if settings.HEALTH_MAINTENANCE_LOCATION and os.path.isfile(
            settings.HEALTH_MAINTENANCE_LOCATION
        ):
            status = "Maintenance"

        return status

    @staticmethod
    def _check_database():
        status = "OK"
        try:
            HomeText.objects.first()
        except Exception as e:
            logging.error(e)
            status = "Error"

        return status

    @staticmethod
    def _check_rabbitmq():
        status = "OK"

        try:
            conn = Connection(
                settings.CELERY_BROKER_URL,
                connect_timeout=1,
                transport_options={"visibility_timeout": 2},
                heartbeat=1,
            )
            conn.ensure_connection(max_retries=2, interval_max=1, interval_start=0)
        except Exception as e:
            logging.error(e)
            status = "Error"

        return status

    @staticmethod
    def _check_celery():
        status = "OK"

        try:
            # Note if rabbitmq down celery retries the connection infinitely
            # should be fixed in celery==4.3.0 https://github.com/celery/celery/issues/2689
            # haproxy returns 503 for any request longer than 60 seconds

            insp = inspect()
            stats = insp.stats()
            if not stats:
                status = "Error"
        except Exception as e:
            logging.error(e)
            status = "Error"

        return status

    @staticmethod
    def _check_email():
        status = "OK"

        try:
            connection = mail.get_connection()
            connection.open()
        except Exception as e:
            logging.error(e)
            status = "Error"

        return status


class VersionView(View):
    def get(self, request, *args, **kwargs):
        return JsonResponse({"version": settings.PACKAGE_VERSION})
