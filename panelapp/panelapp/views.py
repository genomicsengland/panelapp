from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.views.generic import View
from django.views.generic import ListView
from django.http import JsonResponse
from panels.utils import CellBaseConnector
from .models import HomeText


class Homepage(ListView):
    model = HomeText


class HealthCheckView(View):
    def get(self, request, *args, **kwargs):
        if not request.GET.get('health_token') or request.GET.get('health_token') != settings.HEALTH_CHECK_TOKEN:
            raise PermissionDenied

        out = {
            'database': None,
            'cellbase': None
        }

        try:
            HomeText.objects.first()
            out['database'] = "OK"
        except:
            out['database'] = "Error"

        try:
            cb = CellBaseConnector()
            cb.get_coding_transcripts_by_length(["BTK"])
            out['cellbase'] = "OK"
        except Exception as e:
            out['cellbase'] = "Error"

        return JsonResponse(out)
