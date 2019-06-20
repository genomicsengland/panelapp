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
from django.template.loader import render_to_string
from django.contrib.sites.models import Site
from django.conf import settings

from celery import shared_task

from panelapp.tasks import send_email


@shared_task
def registration_email(user_id):
    "Welcome email, sent after registration"

    from .models import User

    user = User.objects.get(pk=user_id)
    text = render_to_string(
        "registration/emails/user_registered.txt", {"user": user, "settings": settings}
    )
    send_email(
        user.email,
        "Thank you for registering, your application is being reviewed",
        text,
    )


@shared_task
def reviewer_confirmation_requset_email(user_id):
    "Send an email to PanelApp curators to check the new reviewer"

    from .models import User

    user = User.objects.get(pk=user_id)
    site = Site.objects.get_current()

    ctx = {
        "user": user,
        "link": "{}/{}/accounts/user/{}/actions/confirm_reviewer/".format(
            settings.PANEL_APP_BASE_URL, settings.ADMIN_URL, user.pk
        ),
        "settings": settings,
    }
    text = render_to_string("registration/emails/reviewer_check_email.txt", ctx)
    send_email(settings.PANEL_APP_EMAIL, "PanelApp Reviewer status request", text)


@shared_task
def revierwer_confirmed_email(user_id):
    "Send an email when user has been confirmed as a reviewer"

    from .models import User

    user = User.objects.get(pk=user_id)
    site = Site.objects.get_current()

    ctx = {"user": user, "site": site, "settings": settings}
    text = render_to_string("registration/emails/reviewer_approved.txt", ctx)
    send_email(
        user.email,
        "Congratulations, you have been approved please authenticate your account",
        text,
    )


@shared_task
def send_verification_email(user_id):
    from .models import User

    user = User.objects.get(pk=user_id)
    site = Site.objects.get_current()

    ctx = {"user": user, "site": site, "settings": settings}
    text = render_to_string("registration/emails/verify_email.txt", ctx)
    send_email(user.email, "Please verify your email address", text)
