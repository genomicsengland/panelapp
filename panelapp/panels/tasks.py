##
## Copyright (c) 2016-2019 Genomics England Ltd.
##
## This file is part of PanelApp
## (see https://panelapp.genomicsengland.co.uk).
##
## Licensed to the Apache Software Foundation (ASF) under one
## or more contributor license agreements.  See the NOTICE file
## distributed with this work for additional information
## regarding copyright ownership.  The ASF licenses this file
## to you under the Apache License, Version 2.0 (the
## "License"); you may not use this file except in compliance
## with the License.  You may obtain a copy of the License at
##
##   http://www.apache.org/licenses/LICENSE-2.0
##
## Unless required by applicable law or agreed to in writing,
## software distributed under the License is distributed on an
## "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
## KIND, either express or implied.  See the License for the
## specific language governing permissions and limitations
## under the License.
##
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
from panels.exceptions import IsSuperPanelException


@shared_task
def promote_panel(user_pk, panel_pk, version_comment):
    from accounts.models import User
    from panels.models import GenePanelSnapshot

    GenePanelSnapshot.objects.get(pk=panel_pk).increment_version(
        major=True, user=User.objects.get(pk=user_pk), comment=version_comment
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
        message = "Panel list successfully imported"
        error = False
    except GeneDoesNotExist as line:
        message = "Line: {} has a wrong gene, please check it and try again.".format(
            line
        )
    except UserDoesNotExist as line:
        message = "Line: {} has a wrong username, please check it and try again.".format(
            line
        )
    except TSVIncorrectFormat as line:
        message = "Line: {} is not properly formatted, please check it and try again.".format(
            line
        )
    except GenesDoNotExist as genes_error:
        message = (
            "Following lines have genes which do not exist in the"
            "database, please check it and try again:\n\n{}".format(genes_error)
        )
    except IsSuperPanelException as e:
        message = "One of the panels contains child panels"
    except Exception as e:
        print(e)
        message = "Unhandled error occured, please forward it to the dev team:\n\n{}".format(
            e
        )

    panel_list.import_log = message
    panel_list.save()

    send_email.delay(
        user.email,
        "Error importing panel list" if error else "Success importing panel list",
        "{}\n\n----\nPanelApp".format(message),
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
        message = "Reviews have been successfully imported"
        error = False
    except GeneDoesNotExist as line:
        message = "Line: {} has a wrong gene, please check it and try again.".format(
            line
        )
    except UserDoesNotExist as line:
        message = "Line: {} has a wrong username, please check it and try again.".format(
            line
        )
    except TSVIncorrectFormat as line:
        message = "Line: {} is not properly formatted, please check it and try again.".format(
            line
        )
    except IncorrectGeneRating as e:
        message = e
    except GenesDoNotExist as genes_error:
        message = (
            "Following lines have genes which do not exist in the"
            "database, please check it and try again:\n\n{}".format(genes_error)
        )
    except IsSuperPanelException as e:
        message = "One of the panels contains child panels"
    except Exception as e:
        print(e)
        message = "There was an error importing reviews"

    panel_list.import_log = message
    panel_list.save()

    send_email.delay(
        user.email,
        "Error importing reviews list" if error else "Success importing reviews list",
        "{}\n\n----\nPanelApp".format(message),
    )


@shared_task
def email_panel_promoted(panel_pk):
    """Emails everyone who contributed to the panel about the new major version"""

    from panels.models import GenePanel

    active_panel = GenePanel.objects.get(pk=panel_pk).active_panel

    subject = "A panel you reviewed has been promoted"
    messages = []

    for contributor in active_panel.contributors:
        if contributor.email:  # check if we have an email in the database
            text = render_to_string(
                "panels/emails/panel_promoted.txt",
                {
                    "first_name": contributor.first_name,
                    "panel_name": active_panel.panel,
                    "panel_id": panel_pk,
                    "settings": settings,
                },
            )

            message = (subject, text, settings.DEFAULT_FROM_EMAIL, [contributor.email])
            messages.append(message)

    logging.debug(
        "Number of emails to send after panel promotion: {}".format(len(messages))
    )
    if messages:
        send_mass_email(tuple(messages))


@shared_task
def background_copy_reviews(user_pk, gene_symbols, panel_from_pk, panel_to_pk):
    from accounts.models import User
    from panels.models import GenePanelSnapshot

    user = User.objects.get(pk=user_pk)

    panels = GenePanelSnapshot.objects.get_active(all=True, internal=True).filter(
        pk__in=[panel_from_pk, panel_to_pk]
    )
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
