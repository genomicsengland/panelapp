from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers
from .viewsets import PanelsViewSet
from .viewsets import ActivityViewSet
from .viewsets import GeneViewSet
from .viewsets import GeneEvaluationsViewSet
from .viewsets import STREvaluationsViewSet
from .viewsets import STRViewSet
from .viewsets import GeneSearchViewSet
from .viewsets import STRSearchViewSet

router = routers.DefaultRouter()
router.register(r'panels', PanelsViewSet, base_name='panels')

genes_router = routers.NestedSimpleRouter(router, r'panels', lookup='panel')
genes_router.register(r'genes', GeneViewSet, base_name='panels_genes')

genes_evaluations_router = routers.NestedSimpleRouter(genes_router, r'genes', lookup='gene')
genes_evaluations_router.register(r'evaluations', GeneEvaluationsViewSet, base_name='genes-evaluations')

strs_router = routers.NestedSimpleRouter(router, r'panels', lookup='panel')
strs_router.register(r'strs', STRViewSet, base_name='panels-strs')

strs_evaluations_router = routers.NestedSimpleRouter(strs_router, r'strs', lookup='str')
strs_evaluations_router.register(r'evaluations', STREvaluationsViewSet, base_name='strs-evaluations')

router.register(r'activities', ActivityViewSet, base_name='activities')
router.register(r'genes', GeneSearchViewSet, base_name='genes')
router.register(r'strs', STRSearchViewSet, base_name='strs')

app_name = 'apiv1'
urlpatterns = [
    path('', include(router.urls)),
    path('', include(genes_router.urls)),
    path('', include(genes_evaluations_router.urls)),
    path('', include(strs_router.urls)),
    path('', include(strs_evaluations_router.urls)),
]
