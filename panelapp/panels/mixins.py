from django.urls import reverse_lazy
from .models import GenePanel


class PanelMixin:
    def get_object(self, *args, **kwargs):
        return GenePanel.objects.get(pk=self.kwargs['pk']).active_panel

    def get_success_url(self):
        return reverse_lazy('panels:detail', kwargs={'pk': self.get_object().panel.pk})
