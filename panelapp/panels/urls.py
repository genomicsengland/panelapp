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
from .views import PanelEditGeneView
from .views import PanelMarkNotReadyView
from .views import DeleteGeneView
from .views import GenePanelSpanshotView


urlpatterns = [
    url(r'^$', PanelsIndexView.as_view(), name="index"),
    url(r'^(?P<pk>[0-9]+)/$', GenePanelView.as_view(), name="detail"),
    url(r'^(?P<pk>[0-9]+)/update$', UpdatePanelView.as_view(), name="update"),
    url(r'^(?P<pk>[0-9]+)/promote$', PromotePanelView.as_view(), name="promote"),
    url(r'^(?P<pk>[0-9]+)/add_gene$', PanelAddGeneView.as_view(), name="add_gene"),
    url(r'^(?P<pk>[0-9]+)/(?P<gene_symbol>[\w\-]+)/evaluation$', GenePanelSpanshotView.as_view(), name="evaluation"),
    url(r'^(?P<pk>[0-9]+)/(?P<gene_symbol>[\w\-]+)/edit$', PanelEditGeneView.as_view(), name="edit_gene"),
    url(r'^(?P<pk>[0-9]+)/(?P<gene_symbol>[\w\-]+)/delete$', DeleteGeneView.as_view(), name="delete_gene"),
    url(r'^(?P<pk>[0-9]+)/(?P<gene_symbol>[\w\-]+)/review$', EmptyView.as_view(), name="review_gene"),

    # TODO Add AJAX calls for clearing details from a Gene
    url(r'^(?P<pk>[0-9]+)/(?P<gene_symbol>[\w\-]+)/clear_gene_sources$',
        EmptyView.as_view(), name="clear_gene_sources"),
    url(r'^(?P<pk>[0-9]+)/(?P<gene_symbol>[\w\-]+)/clear_gene_phenotypes$',
        EmptyView.as_view(), name="clear_gene_phenotypes"),
    url(r'^(?P<pk>[0-9]+)/(?P<gene_symbol>[\w\-]+)/clear_gene_publications$',
        EmptyView.as_view(), name="clear_gene_publications"),
    url(r'^(?P<pk>[0-9]+)/(?P<gene_symbol>[\w\-]+)/clear_gene_mode_of_pathogenicity$',
        EmptyView.as_view(), name="clear_gene_mode_of_pathogenicity"),

    url(r'^(?P<pk>[0-9]+)/mark_not_ready$', PanelMarkNotReadyView.as_view(), name="mark_not_ready"),
    url(r'^create/', CreatePanelView.as_view(), name="create"),

    url(r'^genes/$', GeneListView.as_view(), name="gene_list"),
    url(r'^genes/(?P<slug>[\w\-]+)$', GeneDetailView.as_view(), name="gene_detail"),

    url(r'^admin/', AdminView.as_view(), name="admin"),
    url(r'^upload_genes/', AdminUploadGenesView.as_view(), name="upload_genes"),
    url(r'^upload_panel/', AdminUploadPanelsView.as_view(), name="upload_panels"),
    url(r'^upload_reviews/', AdminUploadReviewsView.as_view(), name="upload_reviews"),

    url(r'^empty/', EmptyView.as_view(), name="empty"),  # used for debuggig
    url(r'^empty/(.+)', EmptyView.as_view(), name="empty_items"),  # used for debugging
]
