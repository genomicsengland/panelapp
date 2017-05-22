from django.core.mail import send_mail
from celery import shared_task
from django.conf import settings


@shared_task
def send_email(email, subject, text, html=None):
    "Send emails via Celery task"

    subject = subject.strip()  # remove new line characters
    send_mail(subject, text, settings.DEFAULT_FROM_EMAIL, recipient_list=[email,], html_message=html)
