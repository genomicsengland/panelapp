from .base import *  # noqa

DEBUG = True

RUNSERVERPLUS_SERVER_ADDRESS_PORT = '0.0.0.0:8000'

INSTALLED_APPS += ('debug_toolbar', 'django_extensions',)  # noqa

MIDDLEWARE += ('debug_toolbar.middleware.DebugToolbarMiddleware',)  # noqa

INTERNAL_IPS = [
    '127.0.0.1',
    '10.0.2.2',  # Vagrant host
]

EMAIL_HOST = 'localhost'
EMAIL_PORT = 25
EMAIL_HOST_USER = 'vagrant'
EMAIL_HOST_PASSWORD = '1'

ALLOWED_HOSTS = ALLOWED_HOSTS + ['localhost', '*']

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

CELERY_BROKER_URL = 'amqp://localhost'
CELERY_TASK_PUBLISH_RETRY_POLICY = {
    "max_retries": 3,
    "interval_start": 0,
    "interval_step": 0.2,
    "interval_max": 0.2
}