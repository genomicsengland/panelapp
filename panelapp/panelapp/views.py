import logging
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.views.generic import View
from django.views.generic import ListView
from django.http import JsonResponse
from django.core import mail
from django.core.mail.backends.smtp import EmailBackend
from kombu import Connection
from .models import HomeText


class Homepage(ListView):
    model = HomeText


class HealthCheckView(View):
    def get(self, request, *args, **kwargs):
        token = request.META.get('TOKEN') if request.META.get('TOKEN') else request.GET.get('token')

        if not settings.HEALTH_CHECK_TOKEN or not token or token != settings.HEALTH_CHECK_TOKEN:
            raise PermissionDenied

        out = {}
        status = 200

        for service in settings.HEALTH_CHECK_SERVICES:
            service_method = getattr(self, '_check_{service}'.format(service=service))
            if callable(service_method):
                out[service] = service_method()
                if out[service] != 'OK':
                    status = 500

        return JsonResponse(out, status=status)

    @staticmethod
    def _check_database():
        status = "OK"
        try:
            HomeText.objects.first()
        except Exception as e:
            logging.error(e)
            status = "Error"

        return status

    @staticmethod
    def _check_rabbitmq():
        status = "OK"

        try:
            conn = Connection(settings.CELERY_BROKER_URL, connect_timeout=1, transport_options={
                'visibility_timeout': 2
            }, heartbeat=1)
            conn.ensure_connection(max_retries=2, interval_max=1, interval_start=0)
        except Exception as e:
            logging.error(e)
            status = "Error"

        return status

    @staticmethod
    def _check_celery():
        status = "OK"

        try:
            # Note if rabbitmq down celery retries the connection infinitely
            # should be fixed in celery==4.3.0 https://github.com/celery/celery/issues/2689
            # haproxy returns 503 for any request longer than 60 seconds

            from celery.task.control import inspect
            insp = inspect()
            stats = insp.stats()
            if not stats:
                status = "Error"
        except Exception as e:
            logging.error(e)
            status = "Error"

        return status

    @staticmethod
    def _check_email():
        status = "OK"

        try:
            connection = mail.get_connection()
            connection.open()
        except Exception as e:
            logging.error(e)
            status = "Error"

        return status


class VersionView(View):
    def get(self, request, *args, **kwargs):
        return JsonResponse({'version': settings.PACKAGE_VERSION})
