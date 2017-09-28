from .base import *  # noqa

PANEL_APP_EMAIL = 'test@localhost'
DEBUG = True
EMAIL_HOST = 'localhost'
EMAIL_PORT = 25
EMAIL_HOST_USER = 'vagrant'
EMAIL_HOST_PASSWORD = '1'

ALLOWED_HOSTS = ['localhost', ]

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

CELERY_ALWAYS_EAGER = True
TEST_RUNNER = 'djcelery.contrib.test_runner.CeleryTestSuiteRunner'
CELERY_TASK_PUBLISH_RETRY_POLICY = {'max_retries': 3}
BROKER_TRANSPORT_OPTIONS = {'socket_timeout': 5}
CELERY_EAGER_PROPAGATES_EXCEPTIONS = True
CELERY_BROKER = 'pyamqp://localhost:5672/'
