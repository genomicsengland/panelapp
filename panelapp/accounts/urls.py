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
from django.conf.urls import include
from django.contrib.auth.views import PasswordResetView
from django.contrib.auth.views import PasswordResetDoneView
from django.contrib.auth.views import PasswordResetConfirmView
from django.contrib.auth.views import PasswordResetCompleteView
from django.urls import reverse_lazy

from .views import UpdatePasswordView
from .views import UserView
from .views import UserRegistrationView
from .views import VerifyEmailAddressView

app_name = "accounts"
urlpatterns = [
    url(r"^profile/$", UserView.as_view(), name="profile"),
    url(r"^registration/$", UserRegistrationView.as_view(), name="register"),
    url(r"^change_password/$", UpdatePasswordView.as_view(), name="change_password"),
    url(
        r"^password_reset/$",
        PasswordResetView.as_view(
            email_template_name="registration/custom_password_reset_email.html",
            template_name="registration/custom_password_reset_form.html",
            success_url=reverse_lazy("accounts:password_reset_done"),
        ),
        name="password_reset",
    ),
    url(
        r"^password_reset/done/$",
        PasswordResetDoneView.as_view(
            template_name="registration/custom_password_change_done.html"
        ),
        name="password_reset_done",
    ),
    url(
        r"^reset/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$",
        PasswordResetConfirmView.as_view(
            template_name="registration/custom_password_reset_confirm.html",
            success_url=reverse_lazy("accounts:password_reset_complete"),
        ),
        name="password_reset_confirm",
    ),
    url(
        r"^reset/done/$",
        PasswordResetCompleteView.as_view(
            template_name="registration/custom_password_change_complete.html"
        ),
        name="password_reset_complete",
    ),
    url("^", include("django.contrib.auth.urls")),
    url(
        r"^verify_email/(?P<b64_email>[a-zA-Z0-9/+]*={0,2})/(?P<crypto_id>[:_\-a-zA-Z0-9/+]*={0,2})/$",
        VerifyEmailAddressView.as_view(),
        name="verify_email",
    ),
]
