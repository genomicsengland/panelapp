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

# Profile used for dockerised deployment on AWS (as opposed to local dockerised environment, for development)
# It uses S3 buckets for static and media files and SQS as Celery backend.

from .base import *  # noqa


# General AWS Settings

# AWS Region (MANDATORY)
AWS_REGION = os.getenv('AWS_REGION')

# AWS Credentials
# DO NOT override for deploying on AWS, where you should be using IAM Roles instead.
# Override them only for special cases or troubleshooting
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID', None)
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY', None)

AWS_DEFAULT_ACL = None  # Actually bypassed by our extended S3 storage, but needed to shut up a warning from s3boto3.py

# Celery backend

# Celery backend broker URL. Override to 'sqs://@localstack:4576' for using LocalStack
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "sqs://")

# Name of the SQS queue. It must match the name of the provisioned SQS queue.
CELERY_TASK_DEFAULT_QUEUE = os.getenv('TASK_QUEUE_NAME', 'panelapp')

# It must match the visibility timeout (seconds) of the provisioned SQS queue.
SQS_QUEUE_VISIBILITY_TIMEOUT = os.getenv('SQS_QUEUE_VISIBILITY_TIMEOUT', 360)

# Broker polling interval (seconds). Override for troubleshooting only
BROKER_POLLING_INTERVAL = os.getenv('BROKER_POLLING_INTERVAL', 1)

BROKER_TRANSPORT_OPTIONS = {
    'region': AWS_REGION,  # FIXME Is Kombo/Boto3 ignoring the region and always using us-east-1?
    'polling_interval': BROKER_POLLING_INTERVAL,      # seconds
    'visibility_timeout': SQS_QUEUE_VISIBILITY_TIMEOUT,  # seconds
}


# File storage

# Use SSL for S3. Optionally override to False for using LocalStack
AWS_S3_USE_SSL = os.getenv('AWS_S3_USE_SSL', True)

# Files ACL. By defualt ('None') inherits bucket ACL. Override to 'public-read' for using LocalStack
AWS_STATICFILES_DEFAULT_ACL = os.getenv('AWS_DEFAULT_ACL', None)

# S3 endpoint. Override to 'http://localstack:4572/' for using LocalStack
AWS_S3_ENDPOINT_URL = os.getenv('AWS_S3_ENDPOINT_URL', None)

# Static files

STATICFILES_STORAGE = 's3_storages.StaticStorage'

# Name of the S3 bucket for static files (MANDATORY).
# Override to `static` with LocalStack.
AWS_S3_STATICFILES_BUCKET_NAME = os.getenv('AWS_S3_STATICFILES_BUCKET_NAME')

# Path, within the S3 bucket, to put static files into
# By default it is `static` (no leading or trailing slash)
AWS_STATICFILES_LOCATION = os.getenv('AWS_STATICFILES_LOCATION', 'static')

# Domain serving static files.
# MANDATORY to override when using a CDN
# Keep the default (`None`) when directly serving files from the bucket (including with LocalStack)
AWS_S3_STATICFILES_CUSTOM_DOMAIN = os.getenv('AWS_S3_STATICFILES_CUSTOM_DOMAIN', None)

# URL of the static files in the S3 bucket. Includes the path defined by AWS_STATICFILES_LOCATION
# and must end with slash.
# Override to 'http://localstack:4572/static-bucket/static/' for using LocalStack
STATIC_URL = os.getenv('STATIC_URL', f'https://{AWS_S3_STATICFILES_CUSTOM_DOMAIN}/{AWS_STATICFILES_LOCATION + ("/" if AWS_STATICFILES_LOCATION else "")}/')

# Files ACL. By default ('None') inherits bucket ACL.
# Override to 'public-read' when using LocalStack
AWS_STATICFILES_DEFAULT_ACL = os.getenv('AWS_DEFAULT_ACL', None)

# Object parameters for static files.
AWS_S3_STATICFILES_OBJECT_PARAMETERS = {'CacheControl': 'max-age=86400'}

# Media files

DEFAULT_FILE_STORAGE = 's3_storages.MediaStorage'

# Name of the S3 bucket for media files (MANDATORY).
# Override to 'media' with LocalStack
AWS_S3_MEDIAFILES_BUCKET_NAME = os.getenv('AWS_S3_MEDIAFILES_BUCKET_NAME')

# Path, within the S3 bucket, to put media files into
# By default it is `media` (no leading or trailing slash)
AWS_MEDIAFILES_LOCATION = os.getenv('AWS_MEDIAFILES_LOCATION', 'media')

# Domain serving media files.
# MANDATORY to override when using a CDN
# Keep the default (`None`) when directly serving files from the bucket (including with LocalStack)
AWS_S3_MEDIAFILES_CUSTOM_DOMAIN = os.getenv('AWS_S3_MEDIAFILES_CUSTOM_DOMAIN', None)

# URL the application fetches media file from.
# Should be `https://<media-bucket-name>.s3.amazonaws.com/uploads/' if AWS_MEDIAFILES_LOCATION is the default 'uploads'.
# Override to 'http://localstack:4572/media-bucket/uploads/' with LocalStack
MEDIA_URL = os.getenv('MEDIA_URL', f'https://{AWS_S3_MEDIAFILES_BUCKET_NAME}.s3.amazonaws.com/{AWS_MEDIAFILES_LOCATION + ("/" if AWS_MEDIAFILES_LOCATION else "")}/')

# Files ACL. By default ('None') inherits bucket ACL. Override to 'public-read' for using LocalStack
AWS_MEDIAFILES_DEFAULT_ACL = os.getenv('AWS_MEDIAFILES_DEFAULT_ACL', None)

# Object parameters for media files.
AWS_S3_MEDIAFILES_OBJECT_PARAMETERS = {}

# Logging (JSON to stdout)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        },
    },
    "formatters": {
        "json" : {
            "class": "simple_json_log_formatter.SimpleJsonFormatter",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": os.getenv("DJANGO_LOG_LEVEL", "INFO"),
        },
        "celery": {
            "handlers": ["console"],
            "level": os.getenv("DJANGO_LOG_LEVEL", "INFO"),
        },
    },
}
