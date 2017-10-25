"""User forms"""

from collections import OrderedDict

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import password_validation

from .models import User
from .models import Reviewer
from .tasks import registration_email
from .tasks import reviewer_confirmation_requset_email


class RegistrationForm(UserCreationForm):
    """Registration form, create user and a linked reviewer"""

    confirm_email = forms.EmailField()
    affiliation = forms.CharField()
    role = forms.ChoiceField(choices=[('', 'Please select a role')] + Reviewer.ROLES)
    workplace = forms.ChoiceField(choices=[('', 'Please select a workspace')] + Reviewer.WORKPLACES)
    group = forms.ChoiceField(choices=[('', 'Please select a group')] + Reviewer.GROUPS)

    class Meta:
        """Select fields"""

        model = User
        fields = ('username', 'first_name', 'last_name', 'email')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        original_fields = self.fields

        self.fields = OrderedDict()
        self.fields['username'] = original_fields.get('username')
        self.fields['first_name'] = original_fields.get('first_name')
        self.fields['last_name'] = original_fields.get('last_name')
        self.fields['email'] = original_fields.get('email')
        self.fields['confirm_email'] = original_fields.get('confirm_email')
        self.fields['password1'] = original_fields.get('password1')
        self.fields['password2'] = original_fields.get('password2')
        self.fields['affiliation'] = original_fields.get('affiliation')
        self.fields['role'] = original_fields.get('role')
        self.fields['workplace'] = original_fields.get('workplace')
        self.fields['group'] = original_fields.get('group')

    def clean_confirm_email(self):
        """Check emails match"""

        email1 = self.cleaned_data.get('email')
        email2 = self.cleaned_data.get('confirm_email')

        if (not email1 or not email2) or email1 and email2 and email1 != email2:
            raise forms.ValidationError("Email confirmation doesn't match")
        
        if User.objects.filter(email=email1):
            raise forms.ValidationError("This email is already registered, please use reset password functionality")

        return email1

    def save(self, *args, **kwargs):
        """Save user and create a reviewer"""

        super().save(*args, **kwargs)

        reviewer = Reviewer()
        reviewer.user = self.instance
        reviewer.affiliation = self.cleaned_data['affiliation']
        reviewer.workplace = self.cleaned_data['workplace']
        reviewer.role = self.cleaned_data['role']
        reviewer.group = self.cleaned_data['group']
        reviewer.save()

        registration_email.delay(self.instance.pk)
        reviewer_confirmation_requset_email.delay(self.instance.pk)


class ChangePasswordForm(forms.Form):
    """Change user's password"""

    current_password = forms.CharField(
        label="Current password",
        strip=False,
        widget=forms.PasswordInput,
    )
    password1 = forms.CharField(
        label="New Password",
        strip=False,
        widget=forms.PasswordInput,
        help_text=password_validation.password_validators_help_text_html(),
    )
    password2 = forms.CharField(
        label="New Password Confirmation",
        widget=forms.PasswordInput,
        strip=False,
        help_text="Enter the same password as before, for verification.",
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs['user']
        del kwargs['user']
        super().__init__(*args, **kwargs)

    def clean_current_password(self):
        """Check if current password match"""

        current_password = self.cleaned_data['current_password']
        if not self.user.check_password(current_password):
            raise forms.ValidationError("Please enter correct password")
        return current_password

    def clean_password2(self):
        """Make sure passwords match"""

        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError(
                "Passwords don't match",
                code='password_mismatch',
            )
        password_validation.validate_password(self.cleaned_data.get('password2'), self.user)
        return password2

    def update_user_password(self, commit=True):
        """Update password"""

        self.user.set_password(self.cleaned_data["password1"])
        self.user.save()
