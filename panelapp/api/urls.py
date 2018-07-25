from django.urls import path, include
from django.conf import settings
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from .permissions import ReadOnlyPermissions

schema_view = get_schema_view(
    openapi.Info(
        title="PanelApp API",
        default_version=settings.REST_FRAMEWORK['DEFAULT_VERSION'],
        description="PanelApp API",
        terms_of_service="https://panelapp.genomicsengland.co.uk/policies/terms/",
        contact=openapi.Contact(email="panelapp@genomicsengland.co.uk"),
        license=openapi.License(name="MIT License"),
    ),
    patterns=['api', ],
    validators=['flex', 'ssv'],
    public=True,
    permission_classes=(ReadOnlyPermissions, ),
)

app_name = 'api'
urlpatterns = [
    path('v1/', include('api.v1.urls', namespace='v1')),
]
