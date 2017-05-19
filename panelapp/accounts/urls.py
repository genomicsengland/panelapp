from django.conf.urls import url
from django.conf.urls import include
from django.contrib.auth.views import PasswordResetView
from django.contrib.auth.views import PasswordResetDoneView
from django.urls import reverse_lazy

from .views import EmptyView

urlpatterns = [
    url(r'^profile/$', EmptyView.as_view(), name="profile"),
    url(r'^registration/$', EmptyView.as_view(), name="register"),
    url(r'^anonymous/$', EmptyView.as_view(), name="anonymous"),
    url(r'^password_reset/done/$', PasswordResetDoneView.as_view(
            template_name="registration/custom_password_change_done.html",
        ), name="password_reset_done"),
    url(r'^password_reset/$', PasswordResetView.as_view(
            email_template_name="registration/custom_password_reset_email.html",
            template_name="registration/custom_password_reset_form.html",
            success_url=reverse_lazy('accounts:password_reset_done')
        ), name="password_reset"),
    url('^', include('django.contrib.auth.urls')),
]
