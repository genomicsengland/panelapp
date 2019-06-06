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

# Profile used for local, dockerised development

from .base import *  # noqa

DEBUG = True

RUNSERVERPLUS_SERVER_ADDRESS_PORT = "0.0.0.0:8000"

INSTALLED_APPS += ("debug_toolbar", "django_extensions",)  # noqa

MIDDLEWARE += ("debug_toolbar.middleware.DebugToolbarMiddleware",)  # noqa

INTERNAL_IPS = ["127.0.0.1"]

EMAIL_HOST = "localhost"
EMAIL_PORT = 25
EMAIL_HOST_USER = None
EMAIL_HOST_PASSWORD = None

ALLOWED_HOSTS = ALLOWED_HOSTS + ["localhost", "*"]

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"


USE_S3 = os.getenv('USE_S3') == 'TRUE'
AWS_REGION = os.getenv('AWS_REGION', "eu-west-2")
AWS_DEFAULT_ACL = 'public-read'  # To shut up a warning from s3boto3.py

if USE_S3:  # Static and Media files on S3

    # AWS settings (regardless using LocalStack or the real thing)
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID', None)
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY', None)

    # What follows is specific to using LocalStack
    AWS_S3_USE_SSL = False
    AWS_S3_ENDPOINT_URL = 'http://localstack:4572/'  # URL used by Boto3 to connect to S3 API

    ###############
    # Static files
    ###############

    # Tell the staticfiles app to use S3Boto3 storage when writing the collected static files
    # (when you run `collectstatic`).
    STATICFILES_STORAGE = 's3_storages.StaticStorage'
    AWS_S3_STATICFILES_BUCKET_NAME = os.getenv('AWS_S3_STATICFILES_BUCKET_NAME')  # Bucket containing staticfiles

    # Location (path) to put media files, in the bucket
    AWS_STATICFILES_LOCATION = os.getenv('AWS_STATICFILES_LOCATION', '')

#   AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'
    AWS_S3_STATICFILES_CUSTOM_DOMAIN = None

    # URL static files are served from
#   STATIC_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/{AWS_LOCATION}/'
    STATIC_URL = f'http://localstack:4572/{AWS_S3_STATICFILES_BUCKET_NAME}/{AWS_STATICFILES_LOCATION + ("/" if AWS_STATICFILES_LOCATION else "")}'  #noqa

    AWS_S3_STATICFILES_OBJECT_PARAMETERS = {'CacheControl': 'max-age=86400'}

    AWS_STATICFILES_DEFAULT_ACL = 'public-read'  # LocalStack only


    ##############
    # Media files
    ##############

    DEFAULT_FILE_STORAGE = 's3_storages.MediaStorage'
    AWS_S3_MEDIAFILES_BUCKET_NAME = os.getenv('AWS_S3_MEDIAFILES_BUCKET_NAME')  # Bucket containing mediafiles
    AWS_MEDIAFILES_LOCATION = os.getenv('AWS_MEDIAFILES_LOCATION', '')  # Location (path) to put media files, in the bucket

    AWS_S3_MEDIAFILES_CUSTOM_DOMAIN = None
    # URL media files are served from
    MEDIA_URL = f'http://localstack:4572/{AWS_S3_MEDIAFILES_BUCKET_NAME}/{AWS_MEDIAFILES_LOCATION + ("/" if AWS_MEDIAFILES_LOCATION else "")}'  #noqa
    AWS_S3_MEDIAFILES_OBJECT_PARAMETERS = {}

    AWS_MEDIAFILES_DEFAULT_ACL = 'public-read'  # LocalStack only

else:  # Static and Media files on local file system

    STATIC_URL = "/static/"
    STATIC_ROOT = os.getenv("STATIC_ROOT")

    MEDIA_URL = "/media/"
    MEDIA_ROOT = os.getenv("MEDIA_ROOT")

##########
# Celery
##########

CELERY_TASK_DEFAULT_QUEUE = "panelapp"  # Statically specify the queue name

CELERY_TASK_PUBLISH_RETRY_POLICY = {
    "max_retries": 3,
    "interval_start": 0,
    "interval_step": 0.2,
    "interval_max": 0.2,
}

USE_SQS = os.getenv('USE_SQS') == 'TRUE'

if USE_SQS:  # Use SQS as message broker

    CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "sqs://@localstack:4576")
    BROKER_TRANSPORT_OPTIONS = {
        'region': AWS_REGION,  # FIXME Is Kombo/Boto3 ignoring the region and always using us-east-1?
        'polling_interval': 1,      # seconds
        'visibility_timeout': 360,  # seconds
    }

else:  # Use RabbitMQ as message broker
    CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "pyamqp://localhost:5672/")
