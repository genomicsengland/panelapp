from django.conf.urls import url
from django.views.generic.base import RedirectView
from django.urls import reverse_lazy

from .views import RedirectGeneView
from .views import RedirectPanelView
from .views import RedirectWebServices
from .views import RedirectGenePanelView

urlpatterns = [
    url(r'^$', RedirectView.as_view(url="/", permanent=True)),
    url(r'^PanelApp/$', RedirectView.as_view(url="/", permanent=True)),
    url(r'^PanelApp/Genes$', RedirectView.as_view(url="/panels/genes/", permanent=True)),
    url(r'^PanelApp/Genes/(?P<gene_symbol>.*)$', RedirectGeneView.as_view(permanent=True)),
    url(r'^PanelApp/PanelBrowser$', RedirectView.as_view(url=reverse_lazy("panels:index"), permanent=True)),
    url(r'^PanelApp/EditPanel/(?P<old_pk>[a-z0-9]+)$', RedirectPanelView.as_view(permanent=True)),
    url(r'^PanelApp/GeneReview/(?P<old_pk>[a-z0-9]+)/(?P<gene_symbol>.*)$',
        RedirectGenePanelView.as_view(permanent=True)),
    url(r'^WebServices/(?P<ws>.*)$', RedirectWebServices.as_view(permanent=True)),
]
