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

INSTALLED_APPS += ("debug_toolbar", "django_extensions")  # noqa

MIDDLEWARE += ("debug_toolbar.middleware.DebugToolbarMiddleware",)  # noqa

INTERNAL_IPS = ["127.0.0.1"]

EMAIL_HOST = "localhost"
EMAIL_PORT = 25
EMAIL_HOST_USER = None
EMAIL_HOST_PASSWORD = None

ALLOWED_HOSTS = ALLOWED_HOSTS + ["localhost", "*"]

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

CELERY_TASK_PUBLISH_RETRY_POLICY = {
    "max_retries": 3,
    "interval_start": 0,
    "interval_step": 0.2,
    "interval_max": 0.2,
}

# Static files and media (uploaded files) to S3 bucket (LocalStack)
# see https://testdriven.io/blog/storing-django-static-and-media-files-on-amazon-s3/
# and https://django-storages.readthedocs.io/en/latest/backends/amazon-S3.html
# and also https://www.caktusgroup.com/blog/2014/11/10/Using-Amazon-S3-to-store-your-Django-sites-static-and-media-files/


USE_S3 = os.getenv('USE_S3') == 'TRUE'

if USE_S3:

    ###############
    # Static files
    ###############

    # Tell the staticfiles app to use S3Boto3 storage when writing the collected static files
    # (when you run `collectstatic`).
    STATICFILES_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

    # AWS settings (regardless using LocalStack or the real thing)
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = os.getenv('AWS_STORAGE_BUCKET_NAME')
    # AWS_LOCATION = 'static'

    AWS_S3_OBJECT_PARAMETERS = {'CacheControl': 'max-age=86400'}

    # What follows is specific to using LocalStack
    AWS_DEFAULT_ACL = 'public-read'
    AWS_S3_USE_SSL = False
    AWS_S3_ENDPOINT_URL = 'http://localstack:4572/'  # URL used by Boto3 to connect to S3 API
#   AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'
#   STATIC_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/{AWS_LOCATION}/'
    STATIC_URL = f'http://localstack:4572/static/'  # URL static files are served from (must end with /)

# FIXME Media file in S3
#  See https://www.caktusgroup.com/blog/2014/11/10/Using-Amazon-S3-to-store-your-Django-sites-static-and-media-files/

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
