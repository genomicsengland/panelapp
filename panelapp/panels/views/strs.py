from django.contrib import messages
from django.views.generic import CreateView
from django.urls import reverse_lazy
from panelapp.mixins import VerifiedReviewerRequiredMixin
from panels.forms import PanelSTRForm
from panels.models import GenePanel
