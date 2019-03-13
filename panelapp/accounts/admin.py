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
from django import forms
from django.contrib import admin
from django.contrib.auth.models import Group
from django_object_actions import DjangoObjectActions
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import ReadOnlyPasswordHashField

from .models import User
from .models import Reviewer


class UserCreationForm(forms.ModelForm):
    """A form for creating new users. Includes all the required
    fields, plus a repeated password."""
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Password confirmation', widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name')

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match")
        return password2

    def save(self, commit=True):
        user = super(UserCreationForm, self).save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class UserChangeForm(forms.ModelForm):
    """A form for updating users. Includes all the fields on
    the user, but replaces the password field with admin's
    password hash display field.
    """
    password = ReadOnlyPasswordHashField(
        label="Password",
        help_text= "Raw passwords are not stored, so there is no way to see this "
                   "user's password, but you can change the password using "
                   "<a href=\"{}\">this form</a>."
    )

    class Meta:
        model = User
        fields = ('email', 'password', 'first_name', 'last_name', 'is_active', 'is_staff')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password'].help_text = self.fields['password'].help_text.format('../password/')
        f = self.fields.get('user_permissions')
        if f is not None:
            f.queryset = f.queryset.select_related('content_type')

    def clean_password(self):
        return self.initial["password"]


class ReviewerInline(admin.StackedInline):
    model = Reviewer


class UserAdmin(DjangoObjectActions, BaseUserAdmin):
    form = UserChangeForm
    add_form = UserCreationForm

    list_display = ('username', 'email', 'first_name', 'last_name', 'is_reviewer', 'is_staff')
    list_filter = ('reviewer__user_type', 'is_staff',)
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name',)}),
        ('Permissions', {'fields': ('is_staff', 'is_active', 'groups',)}),
    )
    superuser_fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name',)}),
        ('Permissions', {'fields': ('is_staff', 'is_superuser', 'is_active', 'groups',)}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'first_name', 'last_name', 'password1', 'password2')
        }),
    )
    search_fields = ('email',)
    ordering = ('email',)
    filter_horizontal = ()

    inlines = [
        ReviewerInline,
    ]

    def get_fieldsets(self, request, obj=None):
        """
        Hook for specifying fieldsets.
        """

        if request.user.is_superuser:
            return self.superuser_fieldsets
        else:
            return self.fieldsets

    def is_reviewer(self, obj):
        try:
            return obj.reviewer.is_REVIEWER()
        except Reviewer.DoesNotExist:
            return False
    is_reviewer.boolean = True

    def confirm_reviewer(self, request, obj):
        try:
            obj.promote_to_reviewer()
        except Reviewer.DoesNotExist:
            pass
    confirm_reviewer.label = "Confirm reviewer"
    confirm_reviewer.short_description = "Confirm reviewer"

    def get_change_actions(self, request, object_id, form_url):
        actions = super().get_change_actions(request, object_id, form_url)

        try:
            obj = self.model.objects.get(pk=object_id)
            if obj.reviewer.is_REVIEWER() or obj.reviewer.is_GEL():
                return []
        except Reviewer.DoesNotExist:
            return []

        return actions

    change_actions = ['confirm_reviewer', ]


class ReviewerAdmin(admin.ModelAdmin):
    model = Reviewer
    list_display = ('reviewer_full_name', 'user_type')
    list_filter = ('user_type', )

    def reviewer_full_name(self, obj):
        return "{} {}".format(obj.user.first_name, obj.user.last_name)


admin.site.register(Reviewer, ReviewerAdmin)
admin.site.register(User, UserAdmin)
