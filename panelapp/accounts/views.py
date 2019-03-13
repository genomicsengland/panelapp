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
from django.http import Http404
from django.views.generic import FormView
from django.views.generic.edit import CreateView
from django.views.generic import DetailView
from django.views.generic import View
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin

from .forms import RegistrationForm
from .forms import ChangePasswordForm
from .models import User


class UserRegistrationView(CreateView):
    template_name = "accounts/user_create.html"

    model = User
    form_class = RegistrationForm

    def form_valid(self, form):
        ret = super().form_valid(form)
        messages.success(
            self.request,
            "Your account has been created. Please confirm your email address by clicking the link we have sent."
        )
        return ret

    def get_success_url(self):
        return reverse_lazy('home')


class UserView(LoginRequiredMixin, DetailView):
    model = User

    def get_object(self, *args, **kwargs):
        return self.request.user


class UpdatePasswordView(LoginRequiredMixin, FormView):
    template_name = "accounts/update_user_password.html"

    form_class = ChangePasswordForm
    success_url = reverse_lazy('accounts:profile')

    def get_form(self, form_class=None):
        if form_class is None:
            form_class = self.get_form_class()
        form_kwargs = self.get_form_kwargs()
        form_kwargs['user'] = self.request.user

        return form_class(**form_kwargs)

    def form_valid(self, form):
        form.update_user_password()
        messages.success(self.request, "Password successfully updated, please login with the new password.")
        return super().form_valid(form)


class VerifyEmailAddressView(View):
    """Verify Email Address

    Before user can login they need to verify their email address.
    The link with email base64 hash and HMAC signed id sent once user registers.
    """

    def get(self, request, *args, **kwargs):
        """Finds user and verifies the payload
        Returns 404 in case it can't find the user, payload invalid or payload expired.
        """

        try:
            user = User.objects.get_by_base64_email(kwargs.get('b64_email'))
            if user.is_active:
                messages.success(request, "Your account has already been verified")
                return redirect('accounts:login')

            if user.verify_crypto_id(kwargs.get('crypto_id')):
                user.activate()
                messages.success(request, "You have successfully verified your email address. You can login now.")
                return redirect('accounts:login')
            else:
                messages.success(request, "The link has expired. We have sent a new link to your email address.")
                user.send_verification_email()
                return redirect('home')
        except User.DoesNotExist:
            raise Http404

        return super().get(request, *args, **kwargs)
