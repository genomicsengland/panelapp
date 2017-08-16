from .base import *  # noqa

DEBUG = True

RUNSERVERPLUS_SERVER_ADDRESS_PORT = '0.0.0.0:8000'

INSTALLED_APPS += ('debug_toolbar', 'django_extensions',)  # noqa

MIDDLEWARE += ('debug_toolbar.middleware.DebugToolbarMiddleware',)  # noqa

INTERNAL_IPS = [
    '127.0.0.1',
    '10.0.2.2',  # Vagrant host
]

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
