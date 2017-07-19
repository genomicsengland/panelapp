from django.views.generic.base import RedirectView
from django.urls import reverse_lazy
from panels.models import GenePanel


class V1RedirectMixin(RedirectView):
    url = "/"

    def dispatch(self, request, *args, **kwargs):
        self.check()

        return super().dispatch(request, *args, **kwargs)


class RedirectGeneView(V1RedirectMixin):
    "Redirect to the list of panels for a specific gene"

    def check(self):
        self.url = reverse_lazy('panels:gene_detail', args=(self.kwargs['gene_symbol'],))


class RedirectPanelView(V1RedirectMixin):
    "Check if we have an id for the old panel and redirect to the new id"

    def check(self):
        try:
            gp = GenePanel.objects.get(old_pk=self.kwargs.get('old_pk'))
            self.url = reverse_lazy('panels:detail', args=(gp.pk,))
        except GenePanel.DoesNotExist:
            self.url = '/panels/'


class RedirectGenePanelView(V1RedirectMixin):
    "Redirect to a gene in a panel"

    def check(self):
        try:
            gp = GenePanel.objects.get(old_pk=self.kwargs.get('old_pk'))
            self.url = reverse_lazy('panels:evalution', args=(gp.pk, self.kwargs.get('gene_symbol')))
        except GenePanel.DoesNotExist:
            self.url = '/panels/'


class RedirectWebServices(V1RedirectMixin):
    "Redirect webservices"

    def check(self):
        self.url = "/WebServices/{}".format(self.kwargs['ws'])
