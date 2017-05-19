from django.conf.urls import url
from django.conf.urls import include

urlpatterns = [
    # add user detail view here
    url('^', include('django.contrib.auth.urls')),
]
