from .base import *  # noqa

DEBUG = True

RUNSERVERPLUS_SERVER_ADDRESS_PORT = '0.0.0.0:8000'

INSTALLED_APPS += (  # noqa
    'debug_toolbar',
    'django_extensions',
    'pympler'
)

MIDDLEWARE += (  # noqa
    'debug_toolbar.middleware.DebugToolbarMiddleware',
)

DEBUG_TOOLBAR_PANELS = [
    'debug_toolbar.panels.versions.VersionsPanel',
    'debug_toolbar.panels.timer.TimerPanel',
    'debug_toolbar.panels.settings.SettingsPanel',
    'debug_toolbar.panels.headers.HeadersPanel',
    'debug_toolbar.panels.request.RequestPanel',
    'debug_toolbar.panels.sql.SQLPanel',
    'debug_toolbar.panels.staticfiles.StaticFilesPanel',
    'debug_toolbar.panels.templates.TemplatesPanel',
    'debug_toolbar.panels.cache.CachePanel',
    'debug_toolbar.panels.signals.SignalsPanel',
    'debug_toolbar.panels.logging.LoggingPanel',
    'debug_toolbar.panels.redirects.RedirectsPanel',
    #'pympler.panels.MemoryPanel',
]

INTERNAL_IPS = [
    '127.0.0.1',
    '10.0.2.2',  # Vagrant host
]

EMAIL_HOST = 'localhost'
EMAIL_PORT = 25
EMAIL_HOST_USER = 'vagrant'
EMAIL_HOST_PASSWORD = '1'

ALLOWED_HOSTS = ALLOWED_HOSTS + ['localhost', ]

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
