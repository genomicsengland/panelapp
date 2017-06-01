from django.urls import reverse_lazy
from django.shortcuts import redirect
from .models import GenePanel


class PanelMixin:
    def get_object(self, *args, **kwargs):
        return GenePanel.objects.get(pk=self.kwargs['pk']).active_panel

    def get_success_url(self):
        return reverse_lazy('panels:detail', kwargs={'pk': self.kwargs['pk']})


class ActAndRedirectMixin:
    def get(self, *args, **kwargs):
        self.act()
        return redirect(self.get_success_url())
