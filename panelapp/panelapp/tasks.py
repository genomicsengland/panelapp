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
from django.core.mail import send_mail
from django.core.mail import send_mass_mail
from django.conf import settings
from .celery import app


@app.task
def send_email(email, subject, text, html=None):
    "Send emails via Celery task"

    subject = subject.strip()  # remove new line characters
    send_mail(subject, text, settings.DEFAULT_FROM_EMAIL, recipient_list=[email, ], html_message=html)


@app.task
def send_mass_email(messages):
    send_mass_mail(messages, fail_silently=False)


@app.task
def ping():
    logging.info('Pong')
    return 'pong'
