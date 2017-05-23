from django.conf.urls import url

from .views import EmptyView
from .views import AdminView


urlpatterns = [
    url(r'^empty/', EmptyView.as_view(), name="empty"),
    url(r'^admin/', AdminView.as_view(), name="admin"),
]
