from django.views.generic.base import View
from django.views.generic.edit import CreateView
from django.shortcuts import render

from .models import User


class EmptyView(View):
    pass


class UserRegistrationView(CreateView):
    model = User
    
