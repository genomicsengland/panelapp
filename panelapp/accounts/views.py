from django.views.generic import FormView
from django.views.generic.edit import CreateView
from django.views.generic import DetailView
from django.contrib import messages
from django.urls import reverse_lazy
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin

from .forms import RegistrationForm
from .forms import ChangePasswordForm
from .models import User


class UserRegistrationView(CreateView):

    model = User
    form_class = RegistrationForm

    def form_valid(self, form):
        ret = super().form_valid(form)
        messages.success(
            self.request,
            "Your account has been created. You can contribute once we confirm your account."
        )
        login(self.request, form.instance)  # login new user
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
