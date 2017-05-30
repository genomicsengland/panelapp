from django.conf.urls import url

from .views import EmptyView
from .views import AdminView
from .views import AdminUploadGenesView
from .views import AdminUploadPanelsView
from .views import AdminUploadReviewsView
from .views import GeneListView
from .views import CreatePanelView
from .views import GeneDetailView
from .views import GenePanelView
from .views import PanelsIndexView
from .views import UpdatePanelView
from .views import PromotePanelView
from .views import PanelAddGeneView

urlpatterns = [
    url(r'^$', PanelsIndexView.as_view(), name="index"),
    url(r'^(?P<pk>[0-9]+)/$', GenePanelView.as_view(), name="detail"),
    url(r'^(?P<pk>[0-9]+)/update$', UpdatePanelView.as_view(), name="update"),
    url(r'^(?P<pk>[0-9]+)/promote$', PromotePanelView.as_view(), name="promote"),
    url(r'^(?P<pk>[0-9]+)/add_gene$', PanelAddGeneView.as_view(), name="add_gene"),
    url(r'^create/', CreatePanelView.as_view(), name="create"),

    url(r'^genes/$', GeneListView.as_view(), name="gene_list"),
    url(r'^genes/(?P<pk>[\w]+)', GeneDetailView.as_view(), name="gene_detail"),

    url(r'^admin/', AdminView.as_view(), name="admin"),
    url(r'^upload_genes/', AdminUploadGenesView.as_view(), name="upload_genes"),
    url(r'^upload_panel/', AdminUploadPanelsView.as_view(), name="upload_panels"),
    url(r'^upload_reviews/', AdminUploadReviewsView.as_view(), name="upload_reviews"),

    url(r'^empty/', EmptyView.as_view(), name="empty"),  # used for debuggig
    url(r'^empty/(.+)', EmptyView.as_view(), name="empty_items"),  # used for debugging
]
