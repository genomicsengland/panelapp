from django.core.exceptions import PermissionDenied


class GELReviewerRequiredMixin:
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.user.reviewer.is_GEL():
            return super().dispatch(request, *args, **kwargs)
        else:
            raise PermissionDenied


class VerifiedReviewerRequiredMixin:
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.user.reviewer.is_verified():
            return super().dispatch(request, *args, **kwargs)
        else:
            raise PermissionDenied
