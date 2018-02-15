from django.contrib import messages
from django.views.generic import CreateView
from django.urls import reverse_lazy
from panelapp.mixins import VerifiedReviewerRequiredMixin
from panels.forms import PanelSTRForm
from panels.models import GenePanel


class PanelAddSTRView(VerifiedReviewerRequiredMixin, CreateView):
    template_name = "panels/genepanel_add_str.html"

    form_class = PanelSTRForm
    name = None

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['panel'] = self.panel
        kwargs['request'] = self.request
        return kwargs

    def get_context_data(self, *args, **kwargs):
        ctx = super().get_context_data(*args, **kwargs)
        ctx['panel'] = self.panel
        return ctx

    @property
    def panel(self):
        return GenePanel.objects.get_active_panel(pk=self.kwargs['pk'])

    def form_valid(self, form):
        form.save_str()
        self.name = form.cleaned_data['name']

        ret = super().form_valid(form)
        msg = "Successfully added a new STR to the panel {}".format(self.panel.panel.name)
        messages.success(self.request, msg)
        return ret

    def get_success_url(self):
        return reverse_lazy('panels:evaluation_str', kwargs={
            'pk': self.kwargs['pk'],
            'str': self.name
        })
