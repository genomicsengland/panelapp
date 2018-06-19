from django.db.models import Q
from dal_select2.views import Select2QuerySetView
from dal_select2.views import Select2ListView
from panels.models import Gene
from panels.models import Evidence
from panels.models import Tag
from panels.models import GenePanelSnapshot


class GeneAutocomplete(Select2QuerySetView):
    def get_queryset(self):
        qs = Gene.objects.filter(active=True)

        if self.q:
            qs = qs.filter(Q(gene_symbol__istartswith=self.q) | Q(gene_name__istartswith=self.q))

        return qs


class SourceAutocomplete(Select2ListView):
    def get_list(self):
        return Evidence.ALL_SOURCES


class TagsAutocomplete(Select2QuerySetView):
    create_field = "name"

    def get_queryset(self):
        qs = Tag.objects.all()

        if self.q:
            qs = qs.filter(Q(name__istartswith=self.q) | Q(name__istartswith=self.q))

        return qs


class SimplePanelsAutocomplete(Select2QuerySetView):
    def get_queryset(self):
        qs = GenePanelSnapshot.objects.get_active_annotated(internal=False, deleted=False).exclude(is_super_panel=True)

        if self.q:
            qs = qs.filter(Q(panel__name__icontains=self.q) | Q(panel__name__icontains=self.q))

        return qs