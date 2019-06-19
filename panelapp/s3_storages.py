#!/usr/bin/env python
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
"""
Custom S3 Storage for static and media file
"""

# S3Boto3Storage cannot be used directly as it does not allow to separate media files from static files, neither by
# path nor bucket
# See https://www.caktusgroup.com/blog/2014/11/10/Using-Amazon-S3-to-store-your-Django-sites-static-and-media-files/

import logging

from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage

logger = logging.getLogger(__name__)


class StaticStorage(S3Boto3Storage):
    region_name = settings.AWS_REGION
    bucket_name = settings.AWS_S3_STATICFILES_BUCKET_NAME
    location = settings.AWS_STATICFILES_LOCATION
    object_parameters = settings.AWS_S3_STATICFILES_OBJECT_PARAMETERS
    custom_domain = settings.AWS_S3_STATICFILES_CUSTOM_DOMAIN
    default_acl = settings.AWS_STATICFILES_DEFAULT_ACL
    querystring_auth = False # We assume static files are public
    logger.debug("Static Files bucket: {}, Location: {}".format(bucket_name, location))


class MediaStorage(S3Boto3Storage):
    region_name = settings.AWS_REGION
    bucket_name = settings.AWS_S3_MEDIAFILES_BUCKET_NAME
    location = settings.AWS_MEDIAFILES_LOCATION
    object_parameters = settings.AWS_S3_MEDIAFILES_OBJECT_PARAMETERS
    custom_domain = settings.AWS_S3_MEDIAFILES_CUSTOM_DOMAIN
    default_acl = settings.AWS_MEDIAFILES_DEFAULT_ACL
    querystring_auth = False # We assume media files are public
    logger.debug("Media Files bucket: {}, Location: {}".format(bucket_name, location))
