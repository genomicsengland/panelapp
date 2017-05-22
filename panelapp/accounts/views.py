from django.views.generic.base import View
from django.views.generic.edit import CreateView
from django.contrib import messages
from django.urls import reverse_lazy
from django.contrib.auth import login

from .forms import RegistrationForm
from .models import User


class EmptyView(View):
    pass


class UserRegistrationView(CreateView):
    template_name = "registration/registration.html"
    model = User
    form_class = RegistrationForm

    def form_valid(self, form):
        ret = super().form_valid(form)
        messages.success(self.request,
            "Your account has been created. You can contribute once we confirm your account."
        )
        login(self.request, form.instance)  # login new user
        return ret

    def get_success_url(self):
        return reverse_lazy('home')
