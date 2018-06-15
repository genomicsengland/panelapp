from django.conf.urls import url
from django.conf.urls import include
from django.contrib.auth.views import PasswordResetView
from django.contrib.auth.views import PasswordResetDoneView
from django.contrib.auth.views import PasswordResetConfirmView
from django.contrib.auth.views import PasswordResetCompleteView
from django.urls import reverse_lazy

from .views import UpdatePasswordView
from .views import UserView
from .views import UserRegistrationView

app_name = 'accounts'
urlpatterns = [
    url(r'^profile/$', UserView.as_view(), name="profile"),
    url(r'^registration/$', UserRegistrationView.as_view(), name="register"),
    url(r'^change_password/$', UpdatePasswordView.as_view(), name="change_password"),
    url(r'^password_reset/$',
        PasswordResetView.as_view(
            email_template_name="registration/custom_password_reset_email.html",
            template_name="registration/custom_password_reset_form.html",
            success_url=reverse_lazy('accounts:password_reset_done')
        ), name="password_reset"),
    url(r'^password_reset/done/$',
        PasswordResetDoneView.as_view(
            template_name="registration/custom_password_change_done.html",
        ), name="password_reset_done"),
    url(r'^reset/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
        PasswordResetConfirmView.as_view(
            template_name="registration/custom_password_reset_confirm.html",
            success_url=reverse_lazy('accounts:password_reset_complete')
        ), name="password_reset_confirm"),
    url(r'^reset/done/$',
        PasswordResetCompleteView.as_view(
            template_name="registration/custom_password_change_complete.html",
        ), name="password_reset_complete"),
    url('^', include('django.contrib.auth.urls')),
]
