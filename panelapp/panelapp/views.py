from django.views.generic import ListView
from .models import HomeText


class Homepage(ListView):
    model = HomeText
