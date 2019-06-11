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

# Gunicorn configuration file
# Iterates through all env variables named GUNICORN_* and set local variables with the suffix, lowercased: e.g.
# GUNICORN_FOO_BAR = 42 creates a local variable named foo_bar with value '42'
# Inspired by: https://sebest.github.io/post/protips-using-gunicorn-inside-a-docker-image/

import os


for k,v in os.environ.items():
    if k.startswith("GUNICORN_"):
        key = k.split('_', 1)[1].lower()
        locals()[key] = v

# Logging

logconfig_dict = {
    'version': 1,
    'disable_existing_loggers': False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        },
    },
    "formatters": {
        "json": {
            "class": "simple_json_log_formatter.SimpleJsonFormatter",
        },
    },
    "loggers" : {
        "root" : {
            "handlers": ["console"],
            "level": os.getenv("DJANGO_LOG_LEVEL", "INFO"),
        },
        "gunicorn.error": {
            "level": os.getenv("DJANGO_LOG_LEVEL", "INFO"),
            "handlers": ["console"],
            "propagate": 1,
            "qualname": "gunicorn.error"
        },
    }
}
