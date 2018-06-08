import datetime
from django.core.exceptions import PermissionDenied
from django.views.generic.base import View
from django.shortcuts import render
from django.utils.functional import cached_property
from django.urls import reverse_lazy
from django.shortcuts import redirect
from django_ajax.mixin import AJAXMixin
from panelapp.mixins import GELReviewerRequiredMixin
from panelapp.mixins import VerifiedReviewerRequiredMixin
from .forms import PanelGeneForm
from .forms import PanelSTRForm
from .forms import GeneReadyForm
from .forms import GeneReviewForm
from .forms import STRReviewForm
from .forms import STRReadyForm
from .forms.ajax import UpdateGeneTagsForm
from .forms.ajax import UpdateGeneMOPForm
from .forms.ajax import UpdateGeneMOIForm
from .forms.ajax import UpdateGenePhenotypesForm
from .forms.ajax import UpdateGenePublicationsForm
from .forms.ajax import UpdateGeneRatingForm
from .forms.ajax import UpdateSTRTagsForm
from .forms.ajax import UpdateSTRMOIForm
from .forms.ajax import UpdateSTRPhenotypesForm
from .forms.ajax import UpdateSTRPublicationsForm
from .forms.ajax import UpdateSTRRatingForm

from .forms.ajax import EditCommentForm
from .models import GenePanel
from .models import GenePanelSnapshot
from .models import Comment
from .views.entities import EntityMixin


class BaseAjaxGeneMixin:
    """Abstract Base Ajax Mixin with methods used by other views.

    Any GET or POST request will call `process` method on the child class or
    throws NotImprementedError in case the method isn't defined
    """

    def process(self):
        raise NotImplementedError

    def get(self, request, *args, **kwargs):
        return self.process()

    def post(self, request, *args, **kwargs):
        return self.process()

    @cached_property
    def panel(self):
        return GenePanel.objects.get(pk=self.kwargs['pk']).active_panel

    @property
    def is_admin(self):
        return self.request.user.is_authenticated and self.request.user.reviewer.is_GEL()


class GeneClearDataAjaxMixin(BaseAjaxGeneMixin, EntityMixin):
    """Mixin for clearing various elements of an entity, for example sources, phenotypes, etc"""

    @cached_property
    def object(self):
        return self.get_object()

    def return_data(self):
        ctx = {
            'entity': self.object,
            'entity_type': self.kwargs['entity_type'],
            'entity_name': self.kwargs['entity_name'],
        }

        if self.is_gene() or (self.object.gene and self.object.gene.get('gene_symbol')):
            ctx['sharing_panels'] = GenePanelSnapshot.objects.get_shared_panels(
                self.object.gene.get('gene_symbol'),
                all=self.is_admin,
                internal=self.is_admin
            )
        else:
            ctx['sharing_panels'] = []

        if self.is_gene():
            ctx.update({
                'panel': self.panel,
                'form_edit': PanelGeneForm(
                    instance=self.object,
                    initial=self.object.get_form_initial(),
                    panel=self.panel,
                    request=self.request
                )
            })
            details = render(self.request, 'panels/genepanelentrysnapshot/details.html', ctx)
        elif self.is_str():
            ctx.update({
                'panel': self.panel,
                'form_edit': PanelSTRForm(
                    instance=self.object,
                    initial=self.object.get_form_initial(),
                    panel=self.panel,
                    request=self.request
                )
            })
            details = render(self.request, 'panels/strs/details.html', ctx)

        return {
            'inner-fragments': {
                '#details': details
            }
        }


class ClearPublicationsAjaxView(GELReviewerRequiredMixin, GeneClearDataAjaxMixin, AJAXMixin, View):
    def process(self):
        self.panel.increment_version()
        del self.panel
        self.object.publications = []
        self.object.save()
        return self.return_data()


class ClearPhoenotypesAjaxView(GELReviewerRequiredMixin, GeneClearDataAjaxMixin, AJAXMixin, View):
    def process(self):
        self.panel.increment_version()
        del self.panel
        self.object.phenotypes = []
        self.object.save()
        return self.return_data()


class ClearModeOfPathogenicityAjaxView(GELReviewerRequiredMixin, GeneClearDataAjaxMixin, AJAXMixin, View):
    def process(self):
        self.panel.increment_version()
        del self.panel
        self.object.mode_of_pathogenicity = ""
        self.object.save()
        return self.return_data()


class ClearSourcesAjaxView(GELReviewerRequiredMixin, GeneClearDataAjaxMixin, AJAXMixin, View):
    def process(self):
        self.panel.increment_version()
        del self.panel
        self.object.clear_evidences(self.request.user)
        self.panel.update_saved_stats()
        return self.return_data()


class ClearSingleSourceAjaxView(EntityMixin, GELReviewerRequiredMixin, BaseAjaxGeneMixin, AJAXMixin, View):
    def get_template_names(self):
        if self.is_gene():
            return "panels/genepanel_table.html"
        elif self.is_str():
            return "panels/strs_table.html"

    def process(self):
        self.panel.increment_version()
        if self.is_gene():
            self.panel.get_gene(self.kwargs['entity_name'])\
                .clear_evidences(self.request.user, evidence=self.kwargs['source'])
        self.panel.update_saved_stats()
        return self.return_data()

    def return_data(self):
        ctx = {
            'panel': self.panel
        }
        table = render(self.request, self.get_template_names(), ctx)
        return {
            'inner-fragments': {
                '#genes_table': table
            }
        }


class PanelAjaxMixin(BaseAjaxGeneMixin):
    template_name = "panels/genepanel_list_table.html"

    def return_data(self):
        if self.request.user.is_authenticated and self.request.user.reviewer.is_GEL():
            panels = GenePanelSnapshot.objects.get_active(True)
        else:
            panels = GenePanelSnapshot.objects.get_active()
        ctx = {
            'panels': panels,
            'view_panels': panels,
        }
        table = render(self.request, self.template_name, ctx)
        return {
            'inner-fragments': {
                '#genes_table': table,
                '#panels_count': len(panels)
            }
        }


class DeletePanelAjaxView(GELReviewerRequiredMixin, PanelAjaxMixin, AJAXMixin, View):
    def process(self):
        GenePanel.objects.get(pk=self.kwargs['pk']).delete()
        return self.return_data()


class RejectPanelAjaxView(GELReviewerRequiredMixin, PanelAjaxMixin, AJAXMixin, View):
    def process(self):
        GenePanel.objects.get(pk=self.kwargs['pk']).reject()
        return self.return_data()


class ApprovePanelAjaxView(GELReviewerRequiredMixin, PanelAjaxMixin, AJAXMixin, View):
    def process(self):
        GenePanel.objects.get(pk=self.kwargs['pk']).approve()
        return self.return_data()


class DeleteEntityAjaxView(EntityMixin, GELReviewerRequiredMixin, BaseAjaxGeneMixin, AJAXMixin, View):
    def get_template_names(self):
        if self.is_gene():
            return "panels/genepanel_table.html"
        elif self.is_str():
            return "panels/strs_table.html"

    def process(self):
        if self.is_gene():
            self.panel.delete_gene(self.kwargs['entity_name'], True, self.request.user)
        elif self.is_str():
            self.panel.delete_str(self.kwargs['entity_name'], True, self.request.user)

        del self.panel
        return self.return_data()

    def return_data(self):
        ctx = {
            'panel': self.panel
        }
        table = render(self.request, self.get_template_names(), ctx)
        return {
            'inner-fragments': {
                '#genes_table' if self.is_gene() else '#strs_table': table  # TODO(Oleg) refactor
            }
        }


class ApproveGeneAjaxView(GELReviewerRequiredMixin, BaseAjaxGeneMixin, AJAXMixin, View):
    template_name = "panels/genepanel_table.html"

    def process(self):
        self.panel.get_gene(self.kwargs['gene_symbol']).approve_gene()  # TODO(Oleg) refactor
        return self.return_data()

    def return_data(self):
        ctx = {
            'panel': self.panel
        }
        table = render(self.request, self.template_name, ctx)
        return {
            'inner-fragments': {
                '#genes_table': table  # TODO(Oleg) refactor
            }
        }


class UpdateEvaluationsMixin(VerifiedReviewerRequiredMixin, BaseAjaxGeneMixin, EntityMixin, AJAXMixin, View):
    @cached_property
    def object(self):
        return self.get_object()

    def get_context_data(self):
        if self.object:
            del self.__dict__['object']

        ctx = {
            'panel': self.panel,
            'entity_type': self.kwargs['entity_type'],
            'entity_name': self.kwargs['entity_name'],
            'entity': self.object,
            'panel_genes': list(self.panel.get_all_genes_extra)
        }

        if self.is_gene() or (self.object.gene and self.object.gene.get('gene_symbol')):
            ctx['sharing_panels'] = GenePanelSnapshot.objects.get_shared_panels(
                self.object.gene.get('gene_symbol'),
                all=self.is_admin,
                internal=self.is_admin
            )
        else:
            ctx['sharing_panels'] = []

        if self.is_gene():
            ctx['feedback_review_parts'] = [
                'Rating',
                'Mode of inheritance',
                'Mode of pathogenicity',
                'Publications',
                'Phenotypes'
            ]
            ctx['form_edit'] = PanelGeneForm(
                instance=self.object,
                initial=self.object.get_form_initial(),
                panel=self.panel,
                request=self.request
            )
            ctx['entity_ready_form'] = GeneReadyForm(
                instance=self.object,
                initial={},
                request=self.request,
            )

            ctx['form'] = GeneReviewForm(
                panel=self.panel,
                request=self.request,
                gene=self.object
            )

            cgi = ctx['panel_genes'].index(self.object)
            ctx['next_gene'] = None if cgi == len(ctx['panel_genes']) - 1 else ctx['panel_genes'][cgi + 1]
            ctx['prev_gene'] = None if cgi == 0 else ctx['panel_genes'][cgi - 1]

            ctx['edit_entity_tags_form'] = UpdateGeneTagsForm(instance=self.object)
            ctx['edit_entity_mop_form'] = UpdateGeneMOPForm(instance=self.object)
            ctx['edit_entity_moi_form'] = UpdateGeneMOIForm(instance=self.object)
            ctx['edit_entity_phenotypes_form'] = UpdateGenePhenotypesForm(instance=self.object)
            ctx['edit_entity_publications_form'] = UpdateGenePublicationsForm(instance=self.object)
            ctx['edit_entity_rating_form'] = UpdateGeneRatingForm(instance=self.object)
        elif self.is_str():
            ctx['form_edit'] = PanelSTRForm(
                instance=self.object,
                initial=self.object.get_form_initial(),
                panel=self.panel,
                request=self.request
            )
            ctx['entity_ready_form'] = STRReadyForm(
                instance=self.object,
                initial={},
                request=self.request,
            )

            ctx['form'] = STRReviewForm(
                panel=self.panel,
                request=self.request,
                str_item=self.object
            )

            ctx['edit_entity_tags_form'] = UpdateSTRTagsForm(instance=self.object)
            ctx['edit_entity_moi_form'] = UpdateSTRMOIForm(instance=self.object)
            ctx['edit_entity_phenotypes_form'] = UpdateSTRPhenotypesForm(instance=self.object)
            ctx['edit_entity_publications_form'] = UpdateSTRPublicationsForm(instance=self.object)
            ctx['edit_entity_rating_form'] = UpdateSTRRatingForm(instance=self.object)

        return ctx

    def return_data(self):
        ctx = self.get_context_data()

        if self.is_gene():
            evaluations = render(self.request, 'panels/entity/evaluate.html', ctx)
            reviews = render(self.request, 'panels/entity/review/review_evaluations.html', ctx)
            details = render(self.request, 'panels/genepanelentrysnapshot/details.html', ctx)
            genes_list = render(self.request, 'panels/entity/evaluation_genes_list.html', ctx)
            history = render(self.request, 'panels/entity/history.html', ctx)
            header = render(self.request, 'panels/entity/header.html', ctx)
        elif self.is_str():
            evaluations = render(self.request, 'panels/entity/evaluate.html', ctx)
            reviews = render(self.request, 'panels/entity/review/review_evaluations.html', ctx)
            details = render(self.request, 'panels/strs/details.html', ctx)
            genes_list = render(self.request, 'panels/entity/evaluation_genes_list.html', ctx)
            history = render(self.request, 'panels/entity/history.html', ctx)
            header = render(self.request, 'panels/entity/header.html', ctx)

        return {
            'inner-fragments': {
                '#evaluate': evaluations,
                '#review-evaluations': reviews,
                '#details': details,
                '#genes_list': genes_list,
                '#history': history,
                '#gene_header': header
            }
        }


class UpdateEntityTagsAjaxView(GELReviewerRequiredMixin, UpdateEvaluationsMixin):
    template_name = "panels/entity/review/part_tags.html"

    @property
    def form_class(self):
        if self.is_gene():
            return UpdateGeneTagsForm
        elif self.is_str():
            return UpdateSTRTagsForm

    def process(self):
        form = self.form_class(instance=self.object, data=self.request.POST)
        if form.is_valid():
            form.save()
            del self.panel
            del self.object
            return self.return_data()
        else:
            return {'status': 400, 'reason': form.errors}

    def return_data(self):
        data = super().return_data()

        ctx = {
            'panel': self.panel,
            'entity': self.object,
            'entity_name': self.kwargs['entity_name'],
            'entity_type': self.kwargs['entity_type'],
            'edit_entity_tags_form': self.form_class(instance=self.object),
            "updated": datetime.datetime.now().strftime('%H:%M:%S')
        }
        tags = render(self.request, self.template_name, ctx)
        data['inner-fragments']['#part-tags'] = tags
        return data


class UpdateEntityMOPAjaxView(GELReviewerRequiredMixin, UpdateEvaluationsMixin):
    template_name = "panels/entity/review/part_mop.html"

    @property
    def form_class(self):
        if self.is_gene():
            return UpdateGeneMOPForm
        return None

    def process(self):
        if self.is_str():
            return {'status': 501, 'reason': 'Not implemented'}

        form = self.form_class(instance=self.object, data=self.request.POST)
        if form.is_valid():
            form.save(user=self.request.user)
            return self.return_data()
        else:
            return {'status': 400, 'reason': form.errors}

    def get_context_data(self):
        ctx = super().get_context_data()
        ctx['edit_entity_mop_form'] = self.form_class(instance=self.object)
        return ctx

    def return_data(self):
        data = super().return_data()
        mop = render(self.request, self.template_name, self.get_context_data())
        data['inner-fragments']['#part-mop'] = mop
        return data


class UpdateEntityMOIAjaxView(GELReviewerRequiredMixin, UpdateEvaluationsMixin):
    template_name = "panels/entity/review/part_moi.html"

    @property
    def form_class(self):
        if self.is_gene():
            return UpdateGeneMOIForm
        elif self.is_str():
            return UpdateSTRMOIForm

    def process(self):
        form = self.form_class(instance=self.object, data=self.request.POST)
        if form.is_valid():
            form.save(user=self.request.user)
            return self.return_data()
        else:
            return {'status': 400, 'reason': form.errors}

    def get_context_data(self):
        ctx = super().get_context_data()
        ctx['edit_entity_moi_form'] = self.form_class(instance=self.object)
        return ctx

    def return_data(self):
        data = super().return_data()
        moi = render(self.request, self.template_name, self.get_context_data())
        data['inner-fragments']['#part-moi'] = moi
        return data


class UpdateEntityPhenotypesAjaxView(GELReviewerRequiredMixin, UpdateEvaluationsMixin):
    template_name = "panels/entity/review/part_phenotypes.html"

    @property
    def form_class(self):
        if self.is_gene():
            return UpdateGenePhenotypesForm
        elif self.is_str():
            return UpdateSTRPhenotypesForm

    def process(self):
        form = self.form_class(instance=self.object, data=self.request.POST)
        if form.is_valid():
            form.save(user=self.request.user)
            return self.return_data()
        else:
            return {'status': 400, 'reason': form.errors}

    def get_context_data(self):
        ctx = super().get_context_data()
        ctx['edit_entity_phenotypes_form'] = self.form_class(instance=self.object)
        return ctx

    def return_data(self):
        data = super().return_data()
        phenotypes = render(self.request, self.template_name, self.get_context_data())
        data['inner-fragments']['#part-phenotypes'] = phenotypes
        return data


class UpdateEntityPublicationsAjaxView(GELReviewerRequiredMixin, UpdateEvaluationsMixin):
    template_name = "panels/entity/review/part_publications.html"

    @property
    def form_class(self):
        if self.is_gene():
            return UpdateGenePublicationsForm
        elif self.is_str():
            return UpdateSTRPublicationsForm

    def process(self):
        form = self.form_class(instance=self.object, data=self.request.POST)
        if form.is_valid():
            form.save(user=self.request.user)
            return self.return_data()
        else:
            return {'status': 400, 'reason': form.errors}

    def get_context_data(self):
        ctx = super().get_context_data()
        ctx['edit_entity_publications_form'] = self.form_class(instance=self.object)
        return ctx

    def return_data(self):
        data = super().return_data()
        publications = render(self.request, self.template_name, self.get_context_data())
        data['inner-fragments']['#part-publications'] = publications
        return data


class UpdateEntityRatingAjaxView(GELReviewerRequiredMixin, UpdateEvaluationsMixin):
    template_name = "panels/entity/review/part_rating.html"

    @property
    def form_class(self):
        if self.is_gene():
            return UpdateGeneRatingForm
        elif self.is_str():
            return UpdateSTRRatingForm

    def process(self):
        form = self.form_class(instance=self.object, data=self.request.POST)
        if form.is_valid():
            form.save(user=self.request.user)
            return self.return_data()
        else:
            return {'status': 400, 'reason': form.errors}

    def get_context_data(self):
        ctx = super().get_context_data()
        ctx['edit_entity_rating_form'] = self.form_class(instance=self.object)
        return ctx

    def return_data(self):
        data = super().return_data()
        rating = render(self.request, self.template_name, self.get_context_data())
        data['inner-fragments']['#part-rating'] = rating
        return data


class DeleteEntityEvaluationAjaxView(UpdateEvaluationsMixin):
    def process(self):
        evaluation_pk = self.kwargs['evaluation_pk']
        self.object.delete_evaluation(evaluation_pk, self.request.user)
        del self.object
        del self.panel
        return self.return_data()


class DeleteEntityCommentAjaxView(UpdateEvaluationsMixin):
    def process(self):
        comment_pk = self.kwargs['comment_pk']
        self.object.delete_comment(comment_pk, self.request.user)
        del self.object
        del self.panel
        return self.return_data()


class SubmitEntityCommentFormAjaxView(VerifiedReviewerRequiredMixin, EntityMixin, BaseAjaxGeneMixin, View):
    @cached_property
    def object(self):
        return self.get_object()

    def process(self):
        comment = Comment.objects.get(pk=self.kwargs['comment_pk'])
        form = EditCommentForm(data=self.request.POST)
        if form.is_valid() and self.request.user == comment.user:
            self.object.edit_comment(comment.pk, self.request.POST.get('comment'))

        return self.return_post_data()

    def post(self, request, *args, **kwargs):
        return self.process()

    def return_post_data(self):
        if self.is_gene():
            kwargs = {
                'pk': self.panel.panel.pk,
                'entity_name': self.object.gene.get('gene_symbol'),
                'entity_type': 'gene'
            }
        elif self.is_str():
            kwargs = {
                'pk': self.panel.panel.pk,
                'entity_name': self.object.name,
                'entity_type': 'str'
            }
        return redirect(reverse_lazy('panels:evaluation', kwargs=kwargs))


class GetEntityCommentFormAjaxView(UpdateEvaluationsMixin):
    def get(self, request, *args, **kwargs):
        return self.return_get_data()

    def return_get_data(self):
        comment = Comment.objects.get(pk=self.kwargs['comment_pk'])
        if comment.user != self.request.user:
            raise PermissionDenied
        edit_comment_form = EditCommentForm(initial={'comment': comment.comment})
        comment_form = render(self.request, 'panels/entity/edit_comment.html', {
            "edit_comment_form": edit_comment_form,
            "panel_id": self.panel.panel.pk,
            'entity_type': self.kwargs['entity_type'],
            "entity_name": self.kwargs['entity_name'],
            "comment_pk": self.kwargs['comment_pk']
        })

        data = {
            'inner-fragments': {
                "#comment_{}".format(self.kwargs['comment_pk']): comment_form
            }
        }

        return data
