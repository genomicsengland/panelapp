import logging
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.views.generic import View
from django.views.generic import ListView
from django.http import JsonResponse
from .models import HomeText
from .tasks import ping


class Homepage(ListView):
    model = HomeText


class HealthCheckView(View):
    def get(self, request, *args, **kwargs):
        if not request.GET.get('health_token') or request.GET.get('health_token') != settings.HEALTH_CHECK_TOKEN:
            raise PermissionDenied

        status = 200
        out = {
            'database': None,
            'rabbitmq': None
        }

        try:
            HomeText.objects.first()
            out['database'] = "OK"
        except Exception as e:
            logging.error(e)
            out['database'] = "Error"
            status = 500

        try:
            ping.delay()
            out['rabbitmq'] = "OK"
        except Exception as e:
            logging.error(e)
            out['rabbitmq'] = "Error"
            status = 500

        return JsonResponse(out, status=status)
