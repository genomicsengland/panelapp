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
from .forms import GeneReadyForm
from .forms import GeneReviewForm
from .forms.ajax import UpdateGeneTagsForm
from .forms.ajax import UpdateGeneMOPForm
from .forms.ajax import UpdateGeneMOIForm
from .forms.ajax import UpdateGenePhenotypesForm
from .forms.ajax import UpdateGenePublicationsForm
from .forms.ajax import UpdateGeneRatingForm
from .forms.ajax import EditCommentForm
from .models import GenePanel
from .models import GenePanelSnapshot
from .models import Comment


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


class GeneClearDataAjaxMixin(BaseAjaxGeneMixin):
    "Mixin for clearing various elements of a gene, for example sources, phenotypes, etc"

    template_name = 'panels/genepanelentrysnapshot/details.html'

    def return_data(self):
        details = render(self.request, self.template_name, {
            'gene': self.gene,
            'panel': self.panel,
            'sharing_panels': GenePanelSnapshot.objects.get_gene_panels(self.kwargs['gene_symbol']),
            'form_edit': PanelGeneForm(
                instance=self.gene,
                initial=self.gene.get_form_initial(),
                panel=self.panel,
                request=self.request
            )
        })

        return {
            'inner-fragments': {
                '#details': details
            }
        }

    @cached_property
    def gene(self):
        return self.panel.get_gene(self.kwargs['gene_symbol'])


class ClearPublicationsAjaxView(GELReviewerRequiredMixin, GeneClearDataAjaxMixin, AJAXMixin, View):
    def process(self):
        self.gene.panel.increment_version()
        del self.gene
        del self.panel
        self.gene.publications = []
        self.gene.save()
        del self.gene
        return self.return_data()


class ClearPhoenotypesAjaxView(GELReviewerRequiredMixin, GeneClearDataAjaxMixin, AJAXMixin, View):
    def process(self):
        self.gene.panel.increment_version()
        del self.gene
        del self.panel
        self.gene.phenotypes = []
        self.gene.save()
        del self.gene

        return self.return_data()


class ClearModeOfPathogenicityAjaxView(GELReviewerRequiredMixin, GeneClearDataAjaxMixin, AJAXMixin, View):
    def process(self):
        self.gene.panel.increment_version()
        del self.gene
        del self.panel
        self.gene.mode_of_pathogenicity = ""
        self.gene.save()
        del self.gene

        return self.return_data()


class ClearSourcesAjaxView(GELReviewerRequiredMixin, GeneClearDataAjaxMixin, AJAXMixin, View):
    def process(self):
        self.gene.panel.increment_version()
        del self.gene
        del self.panel
        self.gene.clear_evidences(self.request.user)
        del self.panel
        del self.gene
        self.gene.panel.update_saved_stats()
        return self.return_data()


class ClearSingleSourceAjaxView(GELReviewerRequiredMixin, GeneClearDataAjaxMixin, AJAXMixin, View):
    template_name = "panels/genepanel_table.html"

    def process(self):
        self.gene.panel.increment_version()
        del self.gene
        del self.panel
        self.gene.clear_evidences(self.request.user, evidence=self.kwargs['source'])
        del self.panel
        del self.gene
        self.gene.panel.update_saved_stats()
        return self.return_data()

    def return_data(self):
        ctx = {
            'panel': self.panel
        }
        table = render(self.request, self.template_name, ctx)
        return {
            'inner-fragments': {
                '#table': table
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
                '#table': table,
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


class DeleteGeneAjaxView(GELReviewerRequiredMixin, BaseAjaxGeneMixin, AJAXMixin, View):
    template_name = "panels/genepanel_table.html"

    def process(self):
        self.panel.delete_gene(self.kwargs['gene_symbol'], True)
        del self.panel
        return self.return_data()

    def return_data(self):
        ctx = {
            'panel': self.panel
        }
        table = render(self.request, self.template_name, ctx)
        return {
            'inner-fragments': {
                '#table': table
            }
        }


class ApproveGeneAjaxView(GELReviewerRequiredMixin, BaseAjaxGeneMixin, AJAXMixin, View):
    template_name = "panels/genepanel_table.html"

    def process(self):
        self.panel.get_gene(self.kwargs['gene_symbol']).approve_gene()
        return self.return_data()

    def return_data(self):
        ctx = {
            'panel': self.panel
        }
        table = render(self.request, self.template_name, ctx)
        return {
            'inner-fragments': {
                '#table': table
            }
        }


class GeneObjectMixin:
    @cached_property
    def gene(self):
        return self.panel.get_gene(self.kwargs['gene_symbol'], prefetch_extra=True)


class UpdateEvaluationsMixin(VerifiedReviewerRequiredMixin, GeneObjectMixin, BaseAjaxGeneMixin, AJAXMixin, View):
    def get_context_data(self):
        if self.panel:
            del self.panel
        if self.gene:
            del self.gene

        ctx = {
            'panel': self.panel,
            'gene': self.gene,
            'form_edit': PanelGeneForm(
                instance=self.gene,
                initial=self.gene.get_form_initial(),
                panel=self.panel,
                request=self.request
            ),
            'gene_ready_form': GeneReadyForm(
                instance=self.gene,
                initial={},
                request=self.request,
            )
        }

        ctx['sharing_panels'] = GenePanelSnapshot.objects.get_gene_panels(self.kwargs['gene_symbol'])
        ctx['feedback_review_parts'] = [
            'Rating',
            'Mode of inheritance',
            'Mode of pathogenicity',
            'Publications',
            'Phenotypes'
        ]
        ctx['form'] = GeneReviewForm(
            panel=self.panel,
            request=self.request,
            gene=self.gene
        )

        ctx['panel_genes'] = list(self.panel.get_all_entries_extra)
        cgi = ctx['panel_genes'].index(self.gene)
        ctx['next_gene'] = None if cgi == len(ctx['panel_genes']) - 1 else ctx['panel_genes'][cgi + 1]
        ctx['prev_gene'] = None if cgi == 0 else ctx['panel_genes'][cgi - 1]

        ctx['edit_gene_tags_form'] = UpdateGeneTagsForm(instance=self.gene)
        ctx['edit_gene_mop_form'] = UpdateGeneMOPForm(instance=self.gene)
        ctx['edit_gene_moi_form'] = UpdateGeneMOIForm(instance=self.gene)
        ctx['edit_gene_phenotypes_form'] = UpdateGenePhenotypesForm(instance=self.gene)
        ctx['edit_gene_publications_form'] = UpdateGenePublicationsForm(instance=self.gene)
        ctx['edit_gene_rating_form'] = UpdateGeneRatingForm(instance=self.gene)

        return ctx

    def return_data(self):
        ctx = self.get_context_data()

        evaluations = render(self.request, 'panels/genepanelentrysnapshot/evaluate.html', ctx)
        reviews = render(self.request, 'panels/genepanelentrysnapshot/review/review_evaluations.html', ctx)
        details = render(self.request, 'panels/genepanelentrysnapshot/details.html', ctx)
        genes_list = render(self.request, 'panels/genepanelentrysnapshot/evaluation_genes_list.html', ctx)
        history = render(self.request, 'panels/genepanelentrysnapshot/history.html', ctx)
        header = render(self.request, 'panels/genepanelentrysnapshot/header.html', ctx)

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


class UpdateGeneTagsAjaxView(GELReviewerRequiredMixin, UpdateEvaluationsMixin):
    template_name = "panels/genepanelentrysnapshot/review/part_tags.html"

    def process(self):
        form = UpdateGeneTagsForm(instance=self.gene, data=self.request.POST)
        if form.is_valid():
            form.save()
            del self.panel
            del self.gene
            return self.return_data()
        else:
            return {'status': 400, 'reason': form.errors}

    def return_data(self):
        data = super().return_data()

        ctx = {
            'panel': self.panel,
            'gene': self.gene,
            'edit_gene_tags_form': UpdateGeneTagsForm(instance=self.gene),
            "updated": datetime.datetime.now().strftime('%H:%M:%S')
        }
        tags = render(self.request, self.template_name, ctx)
        data['inner-fragments']['#part-tags'] = tags
        return data


class UpdateGeneMOPAjaxView(GELReviewerRequiredMixin, UpdateEvaluationsMixin):
    template_name = "panels/genepanelentrysnapshot/review/part_mop.html"

    def process(self):
        form = UpdateGeneMOPForm(instance=self.gene, data=self.request.POST)
        if form.is_valid():
            form.save(user=self.request.user)
            return self.return_data()
        else:
            return {'status': 400, 'reason': form.errors}

    def get_context_data(self):
        ctx = super().get_context_data()
        ctx['edit_gene_mop_form'] = UpdateGeneMOPForm(instance=self.gene)
        return ctx

    def return_data(self):
        data = super().return_data()
        mop = render(self.request, self.template_name, self.get_context_data())
        data['inner-fragments']['#part-mop'] = mop
        return data


class UpdateGeneMOIAjaxView(GELReviewerRequiredMixin, UpdateEvaluationsMixin):
    template_name = "panels/genepanelentrysnapshot/review/part_moi.html"

    def process(self):
        form = UpdateGeneMOIForm(instance=self.gene, data=self.request.POST)
        if form.is_valid():
            form.save(user=self.request.user)
            return self.return_data()
        else:
            return {'status': 400, 'reason': form.errors}

    def get_context_data(self):
        ctx = super().get_context_data()
        ctx['edit_gene_moi_form'] = UpdateGeneMOIForm(instance=self.gene)
        return ctx

    def return_data(self):
        data = super().return_data()
        moi = render(self.request, self.template_name, self.get_context_data())
        data['inner-fragments']['#part-moi'] = moi
        return data


class UpdateGenePhenotypesAjaxView(GELReviewerRequiredMixin, UpdateEvaluationsMixin):
    template_name = "panels/genepanelentrysnapshot/review/part_phenotypes.html"

    def process(self):
        form = UpdateGenePhenotypesForm(instance=self.gene, data=self.request.POST)
        if form.is_valid():
            form.save(user=self.request.user)
            return self.return_data()
        else:
            return {'status': 400, 'reason': form.errors}

    def get_context_data(self):
        ctx = super().get_context_data()
        ctx['edit_gene_phenotypes_form'] = UpdateGenePhenotypesForm(instance=self.gene)
        return ctx

    def return_data(self):
        data = super().return_data()
        phenotypes = render(self.request, self.template_name, self.get_context_data())
        data['inner-fragments']['#part-phenotypes'] = phenotypes
        return data


class UpdateGenePublicationsAjaxView(GELReviewerRequiredMixin, UpdateEvaluationsMixin):
    template_name = "panels/genepanelentrysnapshot/review/part_publications.html"

    def process(self):
        form = UpdateGenePublicationsForm(instance=self.gene, data=self.request.POST)
        if form.is_valid():
            form.save(user=self.request.user)
            return self.return_data()
        else:
            return {'status': 400, 'reason': form.errors}

    def get_context_data(self):
        ctx = super().get_context_data()
        ctx['edit_gene_publications_form'] = UpdateGenePublicationsForm(instance=self.gene)
        return ctx

    def return_data(self):
        data = super().return_data()
        publications = render(self.request, self.template_name, self.get_context_data())
        data['inner-fragments']['#part-publications'] = publications
        return data


class UpdateGeneRatingAjaxView(GELReviewerRequiredMixin, UpdateEvaluationsMixin):
    template_name = "panels/genepanelentrysnapshot/review/part_rating.html"

    def process(self):
        form = UpdateGeneRatingForm(instance=self.gene, data=self.request.POST)
        if form.is_valid():
            form.save(user=self.request.user)
            return self.return_data()
        else:
            return {'status': 400, 'reason': form.errors}

    def get_context_data(self):
        ctx = super().get_context_data()
        ctx['edit_gene_rating_form'] = UpdateGeneRatingForm(instance=self.gene)
        return ctx

    def return_data(self):
        data = super().return_data()
        rating = render(self.request, self.template_name, self.get_context_data())
        data['inner-fragments']['#part-rating'] = rating
        return data


class DeleteGeneEvaluationAjaxView(UpdateEvaluationsMixin):
    def process(self):
        evaluation_pk = self.kwargs['evaluation_pk']
        self.gene.delete_evaluation(evaluation_pk)
        del self.gene
        del self.panel
        return self.return_data()


class DeleteGeneCommentAjaxView(UpdateEvaluationsMixin):
    def process(self):
        comment_pk = self.kwargs['comment_pk']
        self.gene.delete_comment(comment_pk)
        del self.gene
        del self.panel
        return self.return_data()


class SubmitGeneCommentFormAjaxView(VerifiedReviewerRequiredMixin, GeneObjectMixin, BaseAjaxGeneMixin, View):
    def process(self):
        comment = Comment.objects.get(pk=self.kwargs['comment_pk'])
        form = EditCommentForm(data=self.request.POST)
        if form.is_valid() and self.request.user == comment.user:
            self.gene.edit_comment(comment.pk, self.request.POST.get('comment'))

        return self.return_post_data()

    def post(self, request, *args, **kwargs):
        return self.process()

    def return_post_data(self):
        kwargs = {
            'pk': self.panel.panel.pk,
            'gene_symbol': self.gene.gene.get('gene_symbol')
        }
        return redirect(reverse_lazy('panels:evaluation', kwargs=kwargs))


class GetGeneCommentFormAjaxView(UpdateEvaluationsMixin):
    def get(self, request, *args, **kwargs):
        return self.return_get_data()

    def return_get_data(self):
        comment = Comment.objects.get(pk=self.kwargs['comment_pk'])
        if comment.user != self.request.user:
            raise PermissionDenied
        edit_comment_form = EditCommentForm(initial={'comment': comment.comment})
        comment_form = render(self.request, 'panels/genepanelentrysnapshot/edit_comment.html', {
            "edit_comment_form": edit_comment_form,
            "panel_id": self.panel.panel.pk,
            "gene_symbol": self.gene.gene.get('gene_symbol'),
            "comment_pk": self.kwargs['comment_pk']
        })

        data = {
            'inner-fragments': {
                "#comment_{}".format(self.kwargs['comment_pk']): comment_form
            }
        }

        return data
