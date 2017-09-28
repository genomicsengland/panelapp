from django.db import models
from django.db.models import Sum
from django.db.models import Case
from django.db.models import When
from django.db.models import Value
from django.contrib.postgres.aggregates import ArrayAgg
from django.urls import reverse
from django.utils.functional import cached_property
from model_utils.models import TimeStampedModel


class GenePanelManager(models.Manager):
    def get_panel(self, pk):
        if pk.isdigit():
            return super().get_queryset().get(pk=pk)
        else:
            return super().get_queryset().get(old_pk=pk)

    def get_active_panel(self, pk):
        return self.get_panel(pk).active_panel


class GenePanel(TimeStampedModel):
    old_pk = models.CharField(max_length=24, null=True, blank=True, db_index=True)  # Mongo ObjectID hex string
    name = models.CharField(max_length=255, db_index=True)
    approved = models.BooleanField(default=False, db_index=True)
    promoted = models.BooleanField(default=False)
    deleted = models.BooleanField(default=False, db_index=True)

    objects = GenePanelManager()

    def __str__(self):
        ap = self.active_panel
        return "{} version {}.{}".format(self.name, ap.major_version, ap.minor_version)

    def approve(self):
        self.approved = True
        self.save()

    def reject(self):
        self.approved = False
        self.save()

    def get_absolute_url(self):
        return reverse('panels:detail', args=(self.pk,))

    def _prepare_panel_query(self):
        "Returns a queryset for all snapshots ordered by version"

        return self.genepanelsnapshot_set\
            .prefetch_related(
                'panel',
                'level4title',
                'genepanelentrysnapshot_set__evaluation__user',
                'genepanelentrysnapshot_set__evaluation__user__reviewer'
            ).annotate(
                number_of_green_genes=Sum(Case(When(
                    genepanelentrysnapshot__saved_gel_status__gt=3, then=Value(1)),
                    default=Value(0),
                    output_field=models.IntegerField()
                )),
                number_of_amber_genes=Sum(Case(When(
                    genepanelentrysnapshot__saved_gel_status=2, then=Value(1)),
                    default=Value(0),
                    output_field=models.IntegerField()
                )),
                number_of_red_genes=Sum(Case(When(
                    genepanelentrysnapshot__saved_gel_status=1, then=Value(1)),
                    default=Value(0),
                    output_field=models.IntegerField()
                )),
                number_of_gray_genes=Sum(Case(When(
                    genepanelentrysnapshot__saved_gel_status=0, then=Value(1)),
                    default=Value(0),
                    output_field=models.IntegerField()
                ))
            )\
            .order_by('-major_version', '-minor_version', '-created')

    @cached_property
    def active_panel(self):
        "Return the panel with the largest version"

        return self.genepanelsnapshot_set\
            .order_by('-major_version', '-minor_version', '-created').first()

    @property
    def active_panel_extra(self):
        "Return the panel with the largest version and related info"

        return self.genepanelsnapshot_set\
            .prefetch_related(
                'panel',
                'level4title',
                'genepanelentrysnapshot_set',
                'genepanelentrysnapshot_set__tags',
                'genepanelentrysnapshot_set__evidence',
                'genepanelentrysnapshot_set__gene_core',
                'genepanelentrysnapshot_set__evaluation__comments'
            )\
            .order_by('-major_version', '-minor_version', '-created').first()

    def get_panel_version(self, version):
        "Get a specific version. Version argument should be a string"

        major_version, minor_version = version.split('.')
        return self._prepare_panel_query().filter(
            major_version=int(major_version),
            minor_version=int(minor_version)
        ).first()
