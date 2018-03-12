import logging
from django.conf import settings
from django.template.loader import render_to_string
from django.template.defaultfilters import pluralize
from celery import shared_task
from django.db import transaction
from panelapp.tasks import send_email
from panelapp.tasks import send_mass_email
from panels.exceptions import GeneDoesNotExist
from panels.exceptions import GenesDoNotExist
from panels.exceptions import UserDoesNotExist
from panels.exceptions import TSVIncorrectFormat
from panels.exceptions import IncorrectGeneRating


@shared_task
def promote_panel(user_pk, panel_pk, version_comment):
    from accounts.models import User
    from panels.models import GenePanelSnapshot

    GenePanelSnapshot.objects.get(pk=panel_pk).increment_version(
        major=True,
        user=User.objects.get(pk=user_pk),
        comment=version_comment
    )


@shared_task
def import_panel(user_pk, upload_pk):
    """Process large panel lists in the background

    Sends an email to the user once the panel has been imported
    """

    from accounts.models import User
    from panels.models import UploadedPanelList

    user = User.objects.get(pk=user_pk)
    panel_list = UploadedPanelList.objects.get(pk=upload_pk)

    error = True
    try:
        panel_list.process_file(user, background=True)
        message = 'Panel list successfully imported'
        error = False
    except GeneDoesNotExist as line:
        message = 'Line: {} has a wrong gene, please check it and try again.'.format(line)
    except UserDoesNotExist as line:
        message = 'Line: {} has a wrong username, please check it and try again.'.format(line)
    except TSVIncorrectFormat as line:
        message = "Line: {} is not properly formatted, please check it and try again.".format(line)
    except GenesDoNotExist as genes_error:
        message = "Following lines have genes which do not exist in the"\
            "database, please check it and try again:\n\n{}".format(genes_error)
    except Exception as e:
        print(e)
        message = "Unhandled error occured, please forward it to the dev team:\n\n{}".format(e)
    
    panel_list.import_log = message
    panel_list.save()

    send_email.delay(
        user.email,
        'Error importing panel list' if error else 'Success importing panel list',
        "{}\n\n----\nPanelApp".format(message)
    )


@shared_task
def import_reviews(user_pk, review_pk):
    """Process large panel reviews in the background

    Sends an email to the user once the panel has been imported
    """

    from accounts.models import User
    from panels.models import UploadedReviewsList

    user = User.objects.get(pk=user_pk)
    panel_list = UploadedReviewsList.objects.get(pk=review_pk)

    error = True
    try:
        panel_list.process_file(user, background=True)
        message = 'Reviews have been successfully imported'
        error = False
    except GeneDoesNotExist as line:
        message = 'Line: {} has a wrong gene, please check it and try again.'.format(line)
    except UserDoesNotExist as line:
        message = 'Line: {} has a wrong username, please check it and try again.'.format(line)
    except TSVIncorrectFormat as line:
        message = "Line: {} is not properly formatted, please check it and try again.".format(line)
    except IncorrectGeneRating as e:
        message = e
    except GenesDoNotExist as genes_error:
        message = "Following lines have genes which do not exist in the"\
            "database, please check it and try again:\n\n{}".format(genes_error)
    except Exception as e:
        print(e)
        message = "There was an error importing reviews"

    panel_list.import_log = message
    panel_list.save()

    send_email.delay(
        user.email,
        'Error importing reviews list' if error else 'Success importing reviews list',
        "{}\n\n----\nPanelApp".format(message)
    )


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
                    'panel_id': panel_pk,
                    'settings': settings
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


@shared_task
def background_copy_reviews(user_pk, gene_symbols, panel_from_pk, panel_to_pk):
    from accounts.models import User
    from panels.models import GenePanelSnapshot

    user = User.objects.get(pk=user_pk)

    panels = GenePanelSnapshot.objects.get_active(all=True, internal=True).filter(pk__in=[panel_from_pk, panel_to_pk])
    if panels[0].pk == panel_from_pk:
        panel_from = panels[0]
        panel_to = panels[1]
    else:
        panel_to = panels[0]
        panel_from = panels[1]

    try:
        total_count = 0
        with transaction.atomic():
            panel_to = panel_to.increment_version()
            total_count = panel_to.copy_gene_reviews_from(gene_symbols, panel_from)
        subject = "Success copying the reviews"
        message = "{} review{} copied".format(total_count, pluralize(total_count))
    except Exception as e:
        print(e)
        subject = "Error copying reviews"
        message = "There was an error copying the reviews"

    send_email.delay(user.email, subject, "{}\n\n----\nPanelApp".format(message))
