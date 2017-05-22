from django.template.loader import render_to_string
from django.contrib.sites.models import Site
from django.conf import settings

from celery import shared_task

from panelapp.tasks import send_email
from .models import User


@shared_task
def registration_email(user_id):
    "Welcome email, sent after registration"

    user = User.objects.get(pk=user_id)
    text = render_to_string('registration/emails/user_registered.txt', {'user': user})
    send_email(user.email, "Thank you for registering, your application is being reviewed", text)


@shared_task
def reviewer_confirmation_requset_email(user_id):
    "Send an email to PanelApp curators to check the new reviewer"

    user = User.objects.get(pk=user_id)
    site = Site.objects.get_current()

    ctx = {
        'user': user,
        'link': 'https://{}/GeL-admin/accounts/user/{}/change/'.format(site.domain, user.pk)
    }
    text = render_to_string('registration/emails/reviewer_check_email.txt', ctx)
    send_email(settings.PANEL_APP_EMAIL, "PanelApp Reviewer status request", text)
