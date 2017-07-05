from django.core.mail import send_mail
from django.conf import settings
from .celery import app


@app.task
def send_email(email, subject, text, html=None):
    "Send emails via Celery task"

    subject = subject.strip()  # remove new line characters
    send_mail(subject, text, settings.DEFAULT_FROM_EMAIL, recipient_list=[email,], html_message=html)
