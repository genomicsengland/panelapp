from django.views.generic import TemplateView
from django.views.generic.base import View
from django.contrib.auth.mixins import LoginRequiredMixin


class EmptyView(View):
    pass


class GELReviewerRequiredMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)


class AdminView(GELReviewerRequiredMixin, TemplateView):
    template_name = "panels/admin.html"
