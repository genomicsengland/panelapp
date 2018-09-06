from django.template.loader import render_to_string
from django.contrib.sites.models import Site
from django.conf import settings

from celery import shared_task

from panelapp.tasks import send_email


@shared_task
def registration_email(user_id):
    "Welcome email, sent after registration"

    from .models import User

    user = User.objects.get(pk=user_id)
    text = render_to_string('registration/emails/user_registered.txt', {'user': user, 'settings': settings})
    send_email(user.email, "Thank you for registering, your application is being reviewed", text)


@shared_task
def reviewer_confirmation_requset_email(user_id):
    "Send an email to PanelApp curators to check the new reviewer"

    from .models import User

    user = User.objects.get(pk=user_id)
    site = Site.objects.get_current()

    ctx = {
        'user': user,
        'link': '{}/GeL-admin/accounts/user/{}/actions/confirm_reviewer/'.format(settings.PANEL_APP_BASE_URL, user.pk),
        'settings': settings
    }
    text = render_to_string('registration/emails/reviewer_check_email.txt', ctx)
    send_email(settings.PANEL_APP_EMAIL, "PanelApp Reviewer status request", text)


@shared_task
def revierwer_confirmed_email(user_id):
    "Send an email when user has been confirmed as a reviewer"

    from .models import User

    user = User.objects.get(pk=user_id)
    site = Site.objects.get_current()

    ctx = {
        'user': user,
        'site': site,
        'settings': settings
    }
    text = render_to_string('registration/emails/reviewer_approved.txt', ctx)
    send_email(user.email, "Congratulations, you have been approved please authenticate your account", text)


@shared_task
def send_verification_email(user_id):
    from .models import User

    user = User.objects.get(pk=user_id)
    site = Site.objects.get_current()

    ctx = {
        'user': user,
        'site': site,
        'settings': settings
    }
    text = render_to_string('registration/emails/verify_email.txt', ctx)
    send_email(user.email, "Please verify your email address", text)
