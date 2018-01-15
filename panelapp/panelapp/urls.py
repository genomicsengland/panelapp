"""panelapp URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls import url
from django.conf.urls import include
from django.contrib import admin
from .views import Homepage
from .views import HealthCheckView
from .views import VersionView
from .autocomplete import GeneAutocomplete
from .autocomplete import SourceAutocomplete
from .autocomplete import TagsAutocomplete


urlpatterns = [
    url(r'^$', Homepage.as_view(), name="home"),
    url(r'^accounts/', include('accounts.urls', namespace="accounts")),
    url(r'^panels/', include('panels.urls', namespace="panels")),
    url(r'^crowdsourcing/', include('v1rewrites.urls', namespace="v1rewrites")),
    url(r'^WebServices/', include('webservices.urls', namespace="webservices")),
    url(r'^markdownx/', include('markdownx.urls')),
    url(r'^GeL-admin/', admin.site.urls),
    url(r'^autocomplete/gene/$', GeneAutocomplete.as_view(), name="autocomplete-gene"),
    url(r'^autocomplete/source/$', SourceAutocomplete.as_view(), name="autocomplete-source"),
    url(r'^autocomplete/tags/$', TagsAutocomplete.as_view(), name="autocomplete-tags"),
    url(r'^health/$', HealthCheckView.as_view(), name="health_check"),
    url(r'^version/$', VersionView.as_view(), name="version")
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns

    from django.conf.urls.static import static
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
