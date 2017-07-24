import logging
from django.conf import settings
from django.template.loader import render_to_string
from celery import shared_task
from panelapp.tasks import send_mass_email


@shared_task
def email_panel_promoted(panel_pk):
    """Emails everyone who contributed to the panel about the new major version"""

    from panels.models import GenePanel
    active_panel = GenePanel.objects.get(pk=panel_pk).active_panel

    subject = 'A panel you reviewed has been promoted'
    messages = []

    for contributor in active_panel.contributors:
        if contributor[2]:  # check if we have an email in the database
            text = render_to_string(
                'panels/emails/panel_promoted.txt',
                {
                    'first_name': contributor[0],
                    'panel_name': active_panel.panel,
                    'panel_id': panel_pk
                }
            )

            message = (
                subject,
                text,
                settings.DEFAULT_FROM_EMAIL,
                [contributor[2]]
            )
            messages.append(message)

    logging.debug("Number of emails to send after panel promotion: {}".format(len(messages)))
    if messages:
        send_mass_email(tuple(messages))
