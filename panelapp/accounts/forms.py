from collections import OrderedDict

from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import User
from .models import Reviewer
from .tasks import registration_email
from .tasks import reviewer_confirmation_requset_email



class RegistrationForm(UserCreationForm):
    confirm_email = forms.EmailField()
    affiliation = forms.CharField()
    role = forms.ChoiceField(choices=[('','Please select a role')] + Reviewer.ROLES)
    workplace = forms.ChoiceField(choices=[('','Please select a workspace')] + Reviewer.WORKPLACES)
    group = forms.ChoiceField(choices=[('','Please select a group')] + Reviewer.GROUPS)

    class Meta:
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
        email1 = self.cleaned_data.get('email')
        email2 = self.cleaned_data.get('confirm_email')

        if (not email1 or not email2) or email1 and email2 and email1 != email2:
            raise forms.ValidationError("Email confirmation doesn't match")

        return email1

    def save(self, *args, **kwargs):
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
