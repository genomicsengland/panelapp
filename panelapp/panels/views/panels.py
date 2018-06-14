import csv
from datetime import datetime
from django.db.models import Q
from django.contrib import messages
from django.http import HttpResponse
from django.core.exceptions import ValidationError
from django.views.generic import ListView
from django.views.generic import CreateView
from django.views.generic import DetailView
from django.views.generic import UpdateView
from django.views.generic import TemplateView
from django.views.generic import FormView
from django.views.generic import RedirectView
from django.views.generic.base import View
from django.shortcuts import redirect
from django.shortcuts import get_object_or_404
from django.utils.functional import cached_property
from django.urls import reverse_lazy
from django.urls import reverse
from django.utils import timezone
from django.http import StreamingHttpResponse
from panelapp.mixins import GELReviewerRequiredMixin
from accounts.models import User
from panels.forms import PromotePanelForm
from panels.forms import ComparePanelsForm
from panels.forms import PanelForm
from panels.forms import UploadGenesForm
from panels.forms import UploadPanelsForm
from panels.forms import UploadReviewsForm
from panels.forms import ActivityFilterForm
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
                self.objects = GenePanelSnapshot.objects.get_active_annotated(all=True, internal=True)
        else:
            if self.request.GET.get('gene'):
                self.objects = GenePanelSnapshot.objects.get_gene_panels(self.request.GET.get('gene'))
            else:
                self.objects = GenePanelSnapshot.objects.get_active_annotated()
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

        if 'status' in form.changed_data:
            self.instance.add_activity(self.request.user,
                                       'changed panel status to: {}'.format(self.instance.panel.status))

        if 'old_panels' in form.changed_data:
            self.instance.add_activity(self.request.user,
                                       'changed related panels to: {}'.format(', '.join(self.instance.old_panels)))

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
    paginate_by = 100

    def get(self, request, *args, **kwargs):
        if request.GET.get('format', '').lower() == 'csv' and request.user.is_authenticated and request.user.reviewer.is_GEL:
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="export-panelapp-activities-{}.csv"'.format(timezone.now())
            writer = csv.writer(response)
            writer.writerow(['Created', 'Panel', 'Panel ID', 'Panel Version', 'Entity Type', 'Entity Name', 'User', 'Activity'])
            self.object_list = self.get_queryset()
            context = self.get_context_data()
            for activity in context['activities']:
                writer.writerow([
                    activity.created,
                    activity.extra_data.get('panel_name'),
                    activity.extra_data.get('panel_id'),
                    activity.extra_data.get('panel_version'),
                    activity.extra_data.get('entity_type'),
                    activity.extra_data.get('entity_name'),
                    activity.extra_data.get('user_name'),
                    activity.text
                ])
            return response
        return super().get(request, *args, **kwargs)

    def _filter_queryset_kwargs(self):
        filters = {}
        if self.request.user.is_authenticated and self.request.user.reviewer.is_GEL:
            filters = {
                'all': True,
                'deleted': True,
                'internal': True
            }
        return filters

    def available_panels(self):
        return GenePanelSnapshot.objects.get_panels_active_panels(**self._filter_queryset_kwargs())

    def available_panel_versions(self):
        if self.request.GET.get('panel'):
            return GenePanelSnapshot.objects.get_panel_versions(self.request.GET.get('panel'),
                                                                      **self._filter_queryset_kwargs())
        return []

    def available_panel_entities(self):
        if self.request.GET.get('panel') and self.request.GET.get('version'):
            try:
                major_version, minor_version = self.request.GET.get('version').split('.')
                return GenePanelSnapshot.objects.get_panel_entities(self.request.GET.get('panel'),
                                                                    major_version, minor_version,
                                                                    **self._filter_queryset_kwargs())
            except ValueError:
                return []
        elif self.request.GET.get('panel') and self.request.GET.get('entity'):
            return [(self.request.GET.get('entity'), self.request.GET.get('entity'))]
        return []

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data()
        ctx['filter_active'] = True if self.request.GET else False
        form_kwargs = {
            'panels': self.available_panels(),
            'versions': self.available_panel_versions() if self.request.GET.get('panel') else None,
            'entities': self.available_panel_entities() if self.request.GET.get('version') or self.request.GET.get('entity') else None
        }
        ctx['filter_form'] = ActivityFilterForm(self.request.GET if self.request.GET else None, **form_kwargs)
        return ctx

    def get_queryset(self):
        if self.request.user.is_authenticated and self.request.user.reviewer.is_GEL():
            qs = self.model.objects.visible_to_gel()
        else:
            qs = self.model.objects.visible_to_public()

        filter_kwargs = {}

        if self.request.GET.get('panel', '').isdigit():
            filter_kwargs['extra_data__panel_id'] = int(self.request.GET.get('panel'))
        if self.request.GET.get('version'):
            filter_kwargs['extra_data__panel_version'] = self.request.GET.get('version')
        if self.request.GET.get('date_from'):
            filter_kwargs['created__gte'] = self.request.GET.get('date_from')
        if self.request.GET.get('date_to'):
            filter_kwargs['created__lte'] = self.request.GET.get('date_to')

        qs = qs.filter(**filter_kwargs)

        if self.request.GET.get('entity'):
            qs = qs.filter(Q(extra_data__entity_name=self.request.GET.get('entity')) | Q(entity_name=self.request.GET.get('entity')))

        return qs.prefetch_related('user', 'panel', 'user__reviewer')


class DownloadAllPanels(GELReviewerRequiredMixin, View):
    def panel_iterator(self, request):
        yield (
            "Level 4 title",
            "Level 3 title",
            "Level 2 title",
            "URL",
            "Current Version",
            "Version time stamp",
            "# rated genes/total genes",
            "#reviewers",
            "Reviewer name and affiliation (;)",
            "Reviewer emails (;)",
            "Status",
            "Relevant disorders"
        )

        panels = GenePanelSnapshot.objects\
            .get_active_annotated(all=True, internal=True)\
            .prefetch_related(
                'genepanelentrysnapshot_set',
                'genepanelentrysnapshot_set__evaluation',
                'genepanelentrysnapshot_set__evaluation__user',
                'genepanelentrysnapshot_set__evaluation__user__reviewer',
                'str_set__evaluation',
                'str_set__evaluation__user',
                'str_set__evaluation__user__reviewer',
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
                panel.created,
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


class OldCodeURLRedirect(RedirectView):
    """Redirect old code URLs to the new pks"""

    permanent = True

    def dispatch(self, request, *args, **kwargs):
        panel = get_object_or_404(GenePanel, old_pk=kwargs.get('pk'))
        self.url = reverse('panels:detail', args=(panel.id,)) + kwargs.get('uri', '')
        return super().dispatch(request, *args, **kwargs)
