from django.conf.urls import url

from .views import EmptyView
from .views import AdminView
from .views import AdminUploadGenesView
from .views import AdminUploadPanelsView
from .views import AdminUploadReviewsView
from .views import GeneListView
from .views import GeneDetailView

urlpatterns = [
    url(r'^admin/', AdminView.as_view(), name="admin"),
    url(r'^upload_genes/', AdminUploadGenesView.as_view(), name="upload_genes"),
    url(r'^upload_panel/', AdminUploadPanelsView.as_view(), name="upload_panels"),
    url(r'^upload_reviews/', AdminUploadReviewsView.as_view(), name="upload_reviews"),
    url(r'^empty/', EmptyView.as_view(), name="empty"),
    url(r'^genes/$', GeneListView.as_view(), name="gene_list"),
    url(r'^genes/(?P<pk>[\w]+)', GeneDetailView.as_view(), name="gene_detail"),
]
