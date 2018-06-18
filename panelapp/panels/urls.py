from django.conf.urls import url

from django.views.generic import RedirectView
from .views import AdminView
from .views import AdminUploadGenesView
from .views import AdminUploadPanelsView
from .views import AdminUploadReviewsView
from .views import EntitiesListView
from .views import CreatePanelView
from .views import EntityDetailView
from .views import GenePanelView
from .views import PanelsIndexView
from .views import UpdatePanelView
from .views import PromotePanelView
from .views import PanelAddEntityView
from .views import PanelEditEntityView
from .views import PanelMarkNotReadyView
from .views import GenePanelSpanshotView
from .views import EntityReviewView
from .views import MarkEntityReadyView
from .views import DownloadPanelTSVView
from .views import DownloadPanelVersionTSVView
from .views import MarkGeneNotReadyView
from .views import ComparePanelsView
from .views import CompareGeneView
from .views import CopyReviewsView
from .views import DownloadAllGenes
from .views import DownloadAllPanels
from .views import ActivityListView
from .views import DownloadAllSTRs
from .views import GeneDetailRedirectView
from .views import RedirectGenesToEntities
from .views import OldCodeURLRedirect
from .ajax_views import ClearPublicationsAjaxView
from .ajax_views import ClearPhoenotypesAjaxView
from .ajax_views import ClearModeOfPathogenicityAjaxView
from .ajax_views import ClearSourcesAjaxView
from .ajax_views import ClearSingleSourceAjaxView
from .ajax_views import DeletePanelAjaxView
from .ajax_views import DeleteEntityAjaxView
from .ajax_views import RejectPanelAjaxView
from .ajax_views import ApprovePanelAjaxView
from .ajax_views import UpdateEntityTagsAjaxView
from .ajax_views import UpdateEntityMOPAjaxView
from .ajax_views import UpdateEntityMOIAjaxView
from .ajax_views import UpdateEntityPhenotypesAjaxView
from .ajax_views import UpdateEntityPublicationsAjaxView
from .ajax_views import UpdateEntityRatingAjaxView
from .ajax_views import DeleteEntityEvaluationAjaxView
from .ajax_views import GetEntityCommentFormAjaxView
from .ajax_views import DeleteEntityCommentAjaxView
from .ajax_views import SubmitEntityCommentFormAjaxView
from .ajax_views import ApproveGeneAjaxView


app_name = 'panels'

entity_regex = '[\w\-\.\$\~\@\#\ ]+'

urlpatterns = [
    url(r'^$', PanelsIndexView.as_view(), name="index"),
    url(r'^compare/$', ComparePanelsView.as_view(), name="compare_panels_form"),
    url(r'^compare/(?P<panel_1_id>[0-9]+)/(?P<panel_2_id>[0-9]+)$', ComparePanelsView.as_view(), name="compare"),
    url(r'^compare/(?P<panel_1_id>[0-9]+)/(?P<panel_2_id>[0-9]+)/(?P<gene_symbol>[\w\-]+)$',
        CompareGeneView.as_view(), name="compare_genes"),
    url(r'^copy/(?P<panel_1_id>[0-9]+)/(?P<panel_2_id>[0-9]+)$', CopyReviewsView.as_view(), name="copy_reviews"),
    url(r'^(?P<pk>[0-9]+)/$', GenePanelView.as_view(), name="detail"),
    url(r'^(?P<pk>[0-9]+)/update$', UpdatePanelView.as_view(), name="update"),
    url(r'^(?P<pk>[0-9]+)/promote$', PromotePanelView.as_view(), name="promote"),
    url(r'^(?P<pk>[0-9]+)/(?P<entity_type>(gene|str))/add', PanelAddEntityView.as_view(), name="add_entity"),
    url(r'^(?P<pk>[0-9]+)/delete$', DeletePanelAjaxView.as_view(), name="delete_panel"),
    url(r'^(?P<pk>[0-9]+)/reject$', RejectPanelAjaxView.as_view(), name="reject_panel"),
    url(r'^(?P<pk>[0-9]+)/approve$', ApprovePanelAjaxView.as_view(), name="approve_panel"),
    url(r'^(?P<pk>[0-9]+)/download/(?P<categories>[0-4]+)/$',
        DownloadPanelTSVView.as_view(), name="download_panel_tsv"),
    url(r'^(?P<pk>[0-9]+)/download_version/$',
        DownloadPanelVersionTSVView.as_view(), name="download_old_panel_tsv"),
    url(r'^(?P<pk>[0-9]+)/(?P<entity_name>{})/$'.format(entity_regex), RedirectGenesToEntities.as_view(), name="redirect_previous_structure"),
    url(r'^(?P<pk>[0-9]+)/(?P<entity_type>(gene|str))/(?P<entity_name>{})/$'.format(entity_regex), GenePanelSpanshotView.as_view(), name="evaluation"),
    url(r'^(?P<pk>[0-9]+)/(?P<entity_type>(gene|str))/(?P<entity_name>{})/edit$'.format(entity_regex), PanelEditEntityView.as_view(), name="edit_entity"),
    url(r'^(?P<pk>[0-9]+)/(?P<entity_type>(gene|str))/(?P<entity_name>{})/review$'.format(entity_regex), EntityReviewView.as_view(), name="review_entity"),
    url(r'^(?P<pk>[0-9]+)/(?P<entity_type>(gene|str))/(?P<entity_name>{})/mark_as_ready$'.format(entity_regex),
        MarkEntityReadyView.as_view(), name="mark_entity_as_ready"),
    url(r'^(?P<pk>[0-9]+)/(?P<entity_type>(gene|str))/(?P<entity_name>{})/mark_as_not_ready$'.format(entity_regex),
        MarkGeneNotReadyView.as_view(), name="mark_entity_as_not_ready"),

    # AJAX endpoints
    url(r'^(?P<pk>[0-9]+)/(?P<entity_type>(gene|str))/(?P<entity_name>{})/delete$'.format(entity_regex), DeleteEntityAjaxView.as_view(), name="delete_entity"),
    url(r'^(?P<pk>[0-9]+)/(?P<entity_type>(gene|str))/(?P<entity_name>{})/approve$'.format(entity_regex), ApproveGeneAjaxView.as_view(), name="approve_entity"),
    url(r'^(?P<pk>[0-9]+)/(?P<entity_type>(gene|str))/(?P<entity_name>{})/clear_entity_sources$'.format(entity_regex),
        ClearSourcesAjaxView.as_view(), name="clear_entity_sources"),
    url(r'^(?P<pk>[0-9]+)/(?P<entity_type>(gene|str))/(?P<entity_name>{})/clear_entity_source/(?P<source>(.*))/$'.format(entity_regex),
        ClearSingleSourceAjaxView.as_view(), name="clear_entity_source"),
    url(r'^(?P<pk>[0-9]+)/(?P<entity_type>(gene|str))/(?P<entity_name>{})/clear_entity_phenotypes$'.format(entity_regex),
        ClearPhoenotypesAjaxView.as_view(), name="clear_entity_phenotypes"),
    url(r'^(?P<pk>[0-9]+)/(?P<entity_type>(gene|str))/(?P<entity_name>{})/clear_entity_publications$'.format(entity_regex),
        ClearPublicationsAjaxView.as_view(), name="clear_entity_publications"),
    url(r'^(?P<pk>[0-9]+)/(?P<entity_type>(gene|str))/(?P<entity_name>{})/clear_entity_mode_of_pathogenicity$'.format(entity_regex),
        ClearModeOfPathogenicityAjaxView.as_view(), name="clear_entity_mode_of_pathogenicity"),

    # AJAX Review endpoints
    url(r'^(?P<pk>[0-9]+)/(?P<entity_type>(gene|str))/(?P<entity_name>{})/update_entity_tags/$'.format(entity_regex),
        UpdateEntityTagsAjaxView.as_view(), name="update_entity_tags"),
    url(r'^(?P<pk>[0-9]+)/(?P<entity_type>(gene|str))/(?P<entity_name>{})/update_entity_rating/$'.format(entity_regex),
        UpdateEntityRatingAjaxView.as_view(), name="update_entity_rating"),
    url(r'^(?P<pk>[0-9]+)/(?P<entity_type>(gene|str))/(?P<entity_name>{})/update_entity_moi/$'.format(entity_regex),
        UpdateEntityMOIAjaxView.as_view(), name="update_entity_moi"),
    url(r'^(?P<pk>[0-9]+)/(?P<entity_type>(gene|str))/(?P<entity_name>{})/update_entity_mop/$'.format(entity_regex),
        UpdateEntityMOPAjaxView.as_view(), name="update_entity_mop"),
    url(r'^(?P<pk>[0-9]+)/(?P<entity_type>(gene|str))/(?P<entity_name>{})/update_entity_phenotypes/$'.format(entity_regex),
        UpdateEntityPhenotypesAjaxView.as_view(), name="update_entity_phenotypes"),
    url(r'^(?P<pk>[0-9]+)/(?P<entity_type>(gene|str))/(?P<entity_name>{})/update_entity_publications/$'.format(entity_regex),
        UpdateEntityPublicationsAjaxView.as_view(), name="update_entity_publications"),
    url(r'^(?P<pk>[0-9]+)/(?P<entity_type>(gene|str))/(?P<entity_name>{})/delete_evaluation/(?P<evaluation_pk>[0-9]+)/$'.format(entity_regex),
        DeleteEntityEvaluationAjaxView.as_view(), name="delete_evaluation_by_user"),
    url(r'^(?P<pk>[0-9]+)/(?P<entity_type>(gene|str))/(?P<entity_name>{})/edit_comment/(?P<comment_pk>[0-9]+)/$'.format(entity_regex),
        GetEntityCommentFormAjaxView.as_view(), name="edit_comment_by_user"),
    url(r'^(?P<pk>[0-9]+)/(?P<entity_type>(gene|str))/(?P<entity_name>{})/submit_edit_comment/(?P<comment_pk>[0-9]+)/$'.format(entity_regex),
        SubmitEntityCommentFormAjaxView.as_view(), name="submit_edit_comment_by_user"),
    url(r'^(?P<pk>[0-9]+)/(?P<entity_type>(gene|str))/(?P<entity_name>{})/delete_comment/(?P<comment_pk>[0-9]+)/$'.format(entity_regex),
        DeleteEntityCommentAjaxView.as_view(), name="delete_comment_by_user"),

    url(r'^(?P<pk>[0-9]+)/mark_not_ready$'.format(entity_regex), PanelMarkNotReadyView.as_view(), name="mark_not_ready"),
    url(r'^(?P<pk>[a-z0-9]{24})/(?P<uri>.*|$)', OldCodeURLRedirect.as_view(), name="old_code_url_redirect"),
    url(r'^create/', CreatePanelView.as_view(), name="create"),

    url(r'^entities/$', EntitiesListView.as_view(), name="entities_list"),
    url(r'^genes/$', RedirectView.as_view(url='/panels/entities'), name="genes_list"),
    url(r'^entities/(?P<slug>{})$'.format(entity_regex), EntityDetailView.as_view(), name="entity_detail"),
    url(r'^genes/(?P<slug>{})$'.format(entity_regex), GeneDetailRedirectView.as_view()),

    url(r'^activity/$', ActivityListView.as_view(), name="activity"),

    url(r'^admin/', AdminView.as_view(), name="admin"),
    url(r'^upload_genes/', AdminUploadGenesView.as_view(), name="upload_genes"),
    url(r'^download_genes/', DownloadAllGenes.as_view(), name="download_genes"),
    url(r'^download_strs/', DownloadAllSTRs.as_view(), name="download_strs"),
    url(r'^upload_panel/', AdminUploadPanelsView.as_view(), name="upload_panels"),
    url(r'^download_panel/', DownloadAllPanels.as_view(), name="download_panels"),
    url(r'^upload_reviews/', AdminUploadReviewsView.as_view(), name="upload_reviews"),
]
