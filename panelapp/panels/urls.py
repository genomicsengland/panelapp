from django.conf.urls import url

from .views import AdminView
from .views import AdminUploadGenesView
from .views import AdminUploadPanelsView
from .views import AdminUploadReviewsView
from .views import GeneListView
from .views import CreatePanelView
from .views import GeneDetailView
from .views import GenePanelView
from .views import PanelsIndexView
from .views import UpdatePanelView
from .views import PromotePanelView
from .views import PanelAddGeneView
from .views import PanelEditGeneView
from .views import PanelMarkNotReadyView
from .views import GenePanelSpanshotView
from .views import GeneReviewView
from .views import MarkGeneReadyView
from .views import DownloadPanelTSVView
from .views import DownloadPanelVersionTSVView
from .views import MarkGeneNotReadyView
from .views import ComparePanelsView
from .views import CompareGeneView
from .views import CopyReviewsView
from .views import DownloadAllGenes
from .views import DownloadAllPanels
from .views import ActivityListView
from .ajax_views import ClearPublicationsAjaxView
from .ajax_views import ClearPhoenotypesAjaxView
from .ajax_views import ClearModeOfPathogenicityAjaxView
from .ajax_views import ClearSourcesAjaxView
from .ajax_views import ClearSingleSourceAjaxView
from .ajax_views import DeletePanelAjaxView
from .ajax_views import DeleteGeneAjaxView
from .ajax_views import RejectPanelAjaxView
from .ajax_views import ApprovePanelAjaxView
from .ajax_views import UpdateGeneTagsAjaxView
from .ajax_views import UpdateGeneMOPAjaxView
from .ajax_views import UpdateGeneMOIAjaxView
from .ajax_views import UpdateGenePhenotypesAjaxView
from .ajax_views import UpdateGenePublicationsAjaxView
from .ajax_views import UpdateGeneRatingAjaxView
from .ajax_views import DeleteGeneEvaluationAjaxView
from .ajax_views import DeleteGeneCommentAjaxView
from .ajax_views import GetGeneCommentFormAjaxView
from .ajax_views import SubmitGeneCommentFormAjaxView
from .ajax_views import ApproveGeneAjaxView


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
    url(r'^(?P<pk>[0-9]+)/add_gene$', PanelAddGeneView.as_view(), name="add_gene"),
    url(r'^(?P<pk>[0-9]+)/delete$', DeletePanelAjaxView.as_view(), name="delete_panel"),
    url(r'^(?P<pk>[0-9]+)/reject$', RejectPanelAjaxView.as_view(), name="reject_panel"),
    url(r'^(?P<pk>[0-9]+)/approve$', ApprovePanelAjaxView.as_view(), name="approve_panel"),
    url(r'^(?P<pk>[0-9]+)/download/(?P<categories>[0-4]+)/$',
        DownloadPanelTSVView.as_view(), name="download_panel_tsv"),
    url(r'^(?P<pk>[0-9]+)/download_version/$',
        DownloadPanelVersionTSVView.as_view(), name="download_old_panel_tsv"),
    url(r'^(?P<pk>[0-9]+)/(?P<gene_symbol>[\w\-]+)/$', GenePanelSpanshotView.as_view(), name="evaluation"),
    url(r'^(?P<pk>[0-9]+)/(?P<gene_symbol>[\w\-]+)/edit$', PanelEditGeneView.as_view(), name="edit_gene"),
    url(r'^(?P<pk>[0-9]+)/(?P<gene_symbol>[\w\-]+)/review$', GeneReviewView.as_view(), name="review_gene"),
    url(r'^(?P<pk>[0-9]+)/(?P<gene_symbol>[\w\-]+)/mark_as_ready$',
        MarkGeneReadyView.as_view(), name="mark_gene_as_ready"),
    url(r'^(?P<pk>[0-9]+)/(?P<gene_symbol>[\w\-]+)/mark_as_not_ready$',
        MarkGeneNotReadyView.as_view(), name="mark_gene_as_not_ready"),

    # AJAX endpoints
    url(r'^(?P<pk>[0-9]+)/(?P<gene_symbol>[\w\-]+)/delete$', DeleteGeneAjaxView.as_view(), name="delete_gene"),
    url(r'^(?P<pk>[0-9]+)/(?P<gene_symbol>[\w\-]+)/approve$', ApproveGeneAjaxView.as_view(), name="approve_gene"),
    url(r'^(?P<pk>[0-9]+)/(?P<gene_symbol>[\w\-]+)/clear_gene_sources$',
        ClearSourcesAjaxView.as_view(), name="clear_gene_sources"),
    url(r'^(?P<pk>[0-9]+)/(?P<gene_symbol>[\w\-]+)/clear_gene_source/(?P<source>(.*))/$',
        ClearSingleSourceAjaxView.as_view(), name="clear_gene_source"),
    url(r'^(?P<pk>[0-9]+)/(?P<gene_symbol>[\w\-]+)/clear_gene_phenotypes$',
        ClearPhoenotypesAjaxView.as_view(), name="clear_gene_phenotypes"),
    url(r'^(?P<pk>[0-9]+)/(?P<gene_symbol>[\w\-]+)/clear_gene_publications$',
        ClearPublicationsAjaxView.as_view(), name="clear_gene_publications"),
    url(r'^(?P<pk>[0-9]+)/(?P<gene_symbol>[\w\-]+)/clear_gene_mode_of_pathogenicity$',
        ClearModeOfPathogenicityAjaxView.as_view(), name="clear_gene_mode_of_pathogenicity"),

    # AJAX Review endpoints
    url(r'^(?P<pk>[0-9]+)/(?P<gene_symbol>[\w\-]+)/update_gene_tags/$',
        UpdateGeneTagsAjaxView.as_view(), name="update_gene_tags"),
    url(r'^(?P<pk>[0-9]+)/(?P<gene_symbol>[\w\-]+)/update_gene_rating/$',
        UpdateGeneRatingAjaxView.as_view(), name="update_gene_rating"),
    url(r'^(?P<pk>[0-9]+)/(?P<gene_symbol>[\w\-]+)/update_gene_moi/$',
        UpdateGeneMOIAjaxView.as_view(), name="update_gene_moi"),
    url(r'^(?P<pk>[0-9]+)/(?P<gene_symbol>[\w\-]+)/update_gene_mop/$',
        UpdateGeneMOPAjaxView.as_view(), name="update_gene_mop"),
    url(r'^(?P<pk>[0-9]+)/(?P<gene_symbol>[\w\-]+)/update_gene_phenotypes/$',
        UpdateGenePhenotypesAjaxView.as_view(), name="update_gene_phenotypes"),
    url(r'^(?P<pk>[0-9]+)/(?P<gene_symbol>[\w\-]+)/update_gene_publications/$',
        UpdateGenePublicationsAjaxView.as_view(), name="update_gene_publications"),
    url(r'^(?P<pk>[0-9]+)/(?P<gene_symbol>[\w\-]+)/delete_evaluation/(?P<evaluation_pk>[0-9]+)/$',
        DeleteGeneEvaluationAjaxView.as_view(), name="delete_evaluation_by_user"),
    url(r'^(?P<pk>[0-9]+)/(?P<gene_symbol>[\w\-]+)/edit_comment/(?P<comment_pk>[0-9]+)/$',
        GetGeneCommentFormAjaxView.as_view(), name="edit_comment_by_user"),
    url(r'^(?P<pk>[0-9]+)/(?P<gene_symbol>[\w\-]+)/submit_edit_comment/(?P<comment_pk>[0-9]+)/$',
        SubmitGeneCommentFormAjaxView.as_view(), name="submit_edit_comment_by_user"),
    url(r'^(?P<pk>[0-9]+)/(?P<gene_symbol>[\w\-]+)/delete_comment/(?P<comment_pk>[0-9]+)/$',
        DeleteGeneCommentAjaxView.as_view(), name="delete_comment_by_user"),

    url(r'^(?P<pk>[0-9]+)/mark_not_ready$', PanelMarkNotReadyView.as_view(), name="mark_not_ready"),
    url(r'^create/', CreatePanelView.as_view(), name="create"),

    url(r'^genes/$', GeneListView.as_view(), name="gene_list"),
    url(r'^genes/(?P<slug>[\w\.\-~#@*]+)$', GeneDetailView.as_view(), name="gene_detail"),

    url(r'^activity/$', ActivityListView.as_view(), name="activity"),

    url(r'^admin/', AdminView.as_view(), name="admin"),
    url(r'^upload_genes/', AdminUploadGenesView.as_view(), name="upload_genes"),
    url(r'^download_genes/', DownloadAllGenes.as_view(), name="download_genes"),
    url(r'^upload_panel/', AdminUploadPanelsView.as_view(), name="upload_panels"),
    url(r'^download_panel/', DownloadAllPanels.as_view(), name="download_panels"),
    url(r'^upload_reviews/', AdminUploadReviewsView.as_view(), name="upload_reviews"),
]
