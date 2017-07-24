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
    password = ReadOnlyPasswordHashField()

    class Meta:
        model = User
        fields = ('email', 'password', 'first_name', 'last_name', 'is_active', 'is_staff')

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
        ('Permissions', {'fields': ('is_staff',)}),
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
            if obj.reviewer.is_REVIEWER():
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
admin.site.unregister(Group)
