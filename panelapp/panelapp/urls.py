"""panelapp URL Configuration

"""
from django.conf import settings
from django.conf.urls import url
from django.urls import path
from django.conf.urls import include
from django.contrib import admin
from .views import Homepage
from .views import HealthCheckView
from .views import VersionView
from .autocomplete import GeneAutocomplete
from .autocomplete import SourceAutocomplete
from .autocomplete import TagsAutocomplete


urlpatterns = [
    path('', Homepage.as_view(), name="home"),
    path('accounts/', include('accounts.urls', namespace="accounts")),
    path('panels/', include('panels.urls', namespace="panels")),
    path('crowdsourcing/', include('v1rewrites.urls', namespace="v1rewrites")),
    path('WebServices/', include('webservices.urls', namespace="webservices")),
    path('markdownx/', include('markdownx.urls')),
    path('GeL-admin/', admin.site.urls),
    path('autocomplete/gene/', GeneAutocomplete.as_view(), name="autocomplete-gene"),
    path('autocomplete/source/', SourceAutocomplete.as_view(), name="autocomplete-source"),
    path('autocomplete/tags/', TagsAutocomplete.as_view(), name="autocomplete-tags"),
    path('health_check/', HealthCheckView.as_view(), name="health_check"),
    path('version/', VersionView.as_view(), name="version")
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns

    from django.conf.urls.static import static
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
