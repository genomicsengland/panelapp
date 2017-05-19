import os
from .base import *

EMAIL_HOST = "smtp.office365.com"
EMAIL_HOST_USER = 'hhx283@qmul.ac.uk'
EMAIL_HOST_PASSWORD = os.getenv.get('EMAIL_HOST_PASSWORD', None)
EMAIL_PORT = 587
EMAIL_USE_TLS = True
