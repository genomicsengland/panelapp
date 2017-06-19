from django.conf.urls import url
from rest_framework.urlpatterns import format_suffix_patterns
from . import views

# Wire up our API using automatic URL routing.
# Additionally, we include login URLs for the browsable API.
urlpatterns = [
    url(r'^get_panel/(.+)/', views.get_panel, name="get_panel"),
    url(r'^search_genes/(.+)/', views.search_by_gene, name="search_genes"),
    url(r'^list_panels/', views.list_panels, name="list_panels"),
]

urlpatterns = format_suffix_patterns(urlpatterns)
