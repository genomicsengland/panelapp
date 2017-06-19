from django.db import models
from django.db.models import Q
from django.db.models import Sum
from django.db.models import Count
from django.db.models import Case
from django.db.models import When
from django.db.models import Value
from django.utils.functional import cached_property
from model_utils.models import TimeStampedModel


class GenePanelManager(models.Manager):
    def get_panel(self, pk):
        return super().get_queryset().get(Q(pk=pk) | Q(old_pk=pk))

    def get_active_panel(self, pk):
        return self.get_panel(pk).active_panel


class GenePanel(TimeStampedModel):
    old_pk = models.CharField(max_length=24, null=True, blank=True)  # Mongo ObjectID hex string
    name = models.CharField(max_length=255)
    approved = models.BooleanField(default=False)
    promoted = models.BooleanField(default=False)

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

    def _prepare_panel_query(self):
        return self.genepanelsnapshot_set\
            .prefetch_related(
                'panel',
                'level4title',
                'genepanelentrysnapshot_set__evaluation__user',
                'genepanelentrysnapshot_set__evaluation__user__reviewer'
            ).annotate(
                number_of_reviewers=Count('genepanelentrysnapshot__evaluation__user', distinct=True),
                number_of_evaluated_genes=Count('genepanelentrysnapshot__evaluation'),
                number_of_genes=Count('genepanelentrysnapshot'),
                number_of_green_genes=Sum(Case(When(
                    genepanelentrysnapshot__saved_gel_status__gte=4, then=Value(1)),
                    default=Value(0),
                    output_field=models.IntegerField()
                )),
                number_of_amber_genes=Sum(Case(When(
                    genepanelentrysnapshot__saved_gel_status__in=[2, 3], then=Value(1)),
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
            .order_by('-created', '-major_version', '-minor_version')

    @cached_property
    def active_panel(self):
        return self._prepare_panel_query().first()

    def get_panel_version(self, version):
        major_version, minor_version = version.split('.')
        return self._prepare_panel_query().filter(major_version=major_version, minor_version=minor_version).first()
