import csv
from datetime import datetime
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.views.generic import ListView
from django.views.generic import CreateView
from django.views.generic import DetailView
from django.views.generic import UpdateView
from django.views.generic import TemplateView
from django.views.generic import FormView
from django.views.generic.base import View
from django.shortcuts import redirect
from django.utils.functional import cached_property
from django.urls import reverse_lazy
from django.urls import reverse
from django.http import StreamingHttpResponse
from panelapp.mixins import GELReviewerRequiredMixin
from panelapp.mixins import VerifiedReviewerRequiredMixin
from accounts.models import User
from panels.forms import PromotePanelForm
from panels.forms import ComparePanelsForm
from panels.forms import PanelForm
from panels.forms import UploadGenesForm
from panels.forms import UploadPanelsForm
from panels.forms import UploadReviewsForm
from panels.mixins import PanelMixin
from panels.models import ProcessingRunCode
from panels.models import Activity
from panels.models import GenePanel
from panels.models import GenePanelSnapshot
from .entities import EchoWriter


class PanelsIndexView(ListView):
    template_name = "panels/genepanel_list.html"
    model = GenePanelSnapshot
    context_object_name = 'panels'
    objects = []

    def get_queryset(self, *args, **kwargs):
        if self.request.user.is_authenticated and self.request.user.reviewer.is_GEL():
            if self.request.GET.get('gene'):
                self.objects = GenePanelSnapshot.objects.get_gene_panels(self.request.GET.get('gene'), all=True, internal=True)
            else:
                self.objects = GenePanelSnapshot.objects.get_active_anotated(all=True, internal=True)
        else:
            if self.request.GET.get('gene'):
                self.objects = GenePanelSnapshot.objects.get_gene_panels(self.request.GET.get('gene'))
            else:
                self.objects = GenePanelSnapshot.objects.get_active_anotated()
        return self.panels

    @cached_property
    def panels(self):
        return self.objects

    @cached_property
    def compare_panels_form(self):
        return ComparePanelsForm()

    def get_context_data(self, *args, **kwargs):
        ctx = super().get_context_data(*args, **kwargs)
        return ctx


class CreatePanelView(GELReviewerRequiredMixin, CreateView):
    """Create a new panel"""

    template_name = "panels/genepanel_create.html"
    form_class = PanelForm

    def form_valid(self, form):
        self.instance = form.instance
        ret = super().form_valid(form)
        messages.success(self.request, "Successfully added a new panel")
        return ret

    def get_success_url(self):
        return reverse_lazy('panels:detail', kwargs={'pk': self.instance.panel.pk})


class UpdatePanelView(GELReviewerRequiredMixin, PanelMixin, UpdateView):
    """Update panel information"""

    template_name = "panels/genepanel_create.html"
    form_class = PanelForm

    def form_valid(self, form):
        self.instance = form.instance
        ret = super().form_valid(form)
        messages.success(self.request, "Successfully updated the panel")
        return ret


class GenePanelView(DetailView):
    model = GenePanel

    def get_context_data(self, *args, **kwargs):
        ctx = super().get_context_data(*args, **kwargs)
        ctx['panel'] = self.object.active_panel
        ctx['edit'] = PanelForm(
            initial=ctx['panel'].get_form_initial(),
            instance=ctx['panel']
        )
        ctx['contributors'] = User.objects.panel_contributors(ctx['panel'].pk)
        ctx['promote_panel_form'] = PromotePanelForm(
            instance=ctx['panel'],
            request=self.request,
            initial={'version_comment': None}
        )
        return ctx


class AdminContextMixin:
    def get_context_data(self, *args, **kwargs):
        ctx = super().get_context_data(*args, **kwargs)
        ctx['gene_form'] = UploadGenesForm()
        ctx['panel_form'] = UploadPanelsForm()
        ctx['review_form'] = UploadReviewsForm()
        return ctx


class AdminView(GELReviewerRequiredMixin, AdminContextMixin, TemplateView):
    template_name = "panels/admin.html"


class ImportToolMixin(GELReviewerRequiredMixin, AdminContextMixin, FormView):
    template_name = "panels/admin.html"
    success_url = reverse_lazy('panels:admin')

    def form_valid(self, form):
        ret = super().form_valid(form)
        try:
            res = form.process_file(user=self.request.user)
            if res is ProcessingRunCode.PROCESS_BACKGROUND:
                messages.error(self.request, "Import started in the background."
                                               " You will get an email once it has"
                                               " completed.")
            else:
                messages.success(self.request, "Import successful")
        except ValidationError as errors:
            for error in errors:
                messages.error(self.request, error)
        return ret


class AdminUploadGenesView(ImportToolMixin, AdminContextMixin):
    form_class = UploadGenesForm

    def get(self, request, *args, **kwargs):
        return redirect(reverse_lazy('panels:admin'))


class AdminUploadPanelsView(ImportToolMixin, AdminContextMixin):
    form_class = UploadPanelsForm

    def get(self, request, *args, **kwargs):
        return redirect(reverse_lazy('panels:admin'))


class AdminUploadReviewsView(ImportToolMixin, AdminContextMixin):
    form_class = UploadReviewsForm

    def get(self, request, *args, **kwargs):
        return redirect(reverse_lazy('panels:admin'))

class PromotePanelView(GELReviewerRequiredMixin, GenePanelView, UpdateView):
    template_name = "panels/genepanel_detail.html"
    form_class = PromotePanelForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        kwargs['instance'] = self.object.active_panel
        return kwargs

    def form_valid(self, form):
        ret = super().form_valid(form)
        self.instance = form.instance.panel
        messages.success(self.request, "Panel {} will be promoted in a few moments.".format(self.get_object().name))
        return ret

    def get_success_url(self):
        return self.get_object().get_absolute_url()


class ActivityListView(ListView):
    model = Activity
    context_object_name = 'activities'
    paginate_by = 3000

    def get_queryset(self):
        if self.request.user.is_authenticated and self.request.user.reviewer.is_GEL():
            qs = self.model.objects.visible_to_gel()
        else:
            qs = self.model.objects.visible_to_public()

        qs = qs.prefetch_related('user', 'panel', 'user__reviewer')
        return qs


class DownloadAllPanels(GELReviewerRequiredMixin, View):
    def panel_iterator(self, request):
        yield (
            "Level 4 title",
            "Level 3 title",
            "Level 2 title",
            "URL",
            "Current Version",
            "# rated genes/total genes",
            "#reviewers",
            "Reviewer name and affiliation (;)",
            "Reviewer emails (;)",
            "Status",
            "Relevant disorders"
        )

        panels = GenePanelSnapshot.objects\
            .get_active_anotated(all=True, internal=True)\
            .prefetch_related(
                'genepanelentrysnapshot_set',
                'genepanelentrysnapshot_set__evaluation',
                'genepanelentrysnapshot_set__evaluation__user',
                'genepanelentrysnapshot_set__evaluation__user__reviewer',
            )\
            .all()

        for panel in panels:
            rate = "{} of {} genes reviewed".format(panel.number_of_evaluated_genes, panel.number_of_genes)
            reviewers = panel.contributors
            contributors = [
                "{} {} ({})".format(user[0], user[1], user[3]) if user[0] else user[4]
                for user in reviewers
                if user[4]
            ]

            yield (
                panel.level4title.name,
                panel.level4title.level3title,
                panel.level4title.level2title,
                request.build_absolute_uri(reverse('panels:detail', args=(panel.panel.id,))),
                panel.version,
                rate,
                len(reviewers),
                ";".join(contributors),  # aff
                ";".join([user[2] for user in reviewers if user[2]]),  # email
                panel.panel.status.upper(),
                ";".join(panel.old_panels)
            )

    def get(self, request, *args, **kwargs):
        pseudo_buffer = EchoWriter()
        writer = csv.writer(pseudo_buffer, delimiter='\t')

        response = StreamingHttpResponse((writer.writerow(row) for row in self.panel_iterator(request)),
                                         content_type='text/tab-separated-values')
        attachment = 'attachment; filename=All_panels_{}.tsv'.format(
            datetime.now().strftime('%Y%m%d-%H%M'))
        response['Content-Disposition'] = attachment
        return response

