from django.db import models
from django.db.models import Sum
from django.db.models import Count
from django.db.models import Case
from django.db.models import When
from django.db.models import Value
from django.db.models import Subquery
from django.contrib.postgres.fields import ArrayField
from django.db.models import IntegerField
from django.utils.functional import cached_property
from model_utils.models import TimeStampedModel

from .genepanel import GenePanel
from .level4title import Level4Title


class GenePanelSnapshotManager(models.Manager):
    def get_latest_ids(self):
        return super().get_queryset()\
            .distinct('panel')\
            .values('pk')\
            .order_by('panel', '-major_version', '-minor_version')

    def get_active(self):
        return super().get_queryset()\
            .prefetch_related('panel', 'level4title')\
            .filter(pk__in=Subquery(self.get_latest_ids()))\
            .annotate(
                number_of_reviewers=Count('genepanelentrysnapshot__evaluation__user', distinct=True),
                number_of_evaluated_genes=Count('genepanelentrysnapshot__evaluation'),
                number_of_genes=Count('genepanelentrysnapshot'),
            )\
            .order_by('panel', '-major_version', '-minor_version')

    def get_gene_panels(self, gene_symbol):
        return self.get_active().filter(genepanelentrysnapshot__gene__gene_symbol=gene_symbol)


class GenePanelSnapshot(TimeStampedModel):
    class Meta:
        get_latest_by = "created"
        ordering = ['-created', '-major_version', '-minor_version']

    objects = GenePanelSnapshotManager()

    level4title = models.ForeignKey(Level4Title)
    panel = models.ForeignKey(GenePanel)
    major_version = models.IntegerField(default=0)
    minor_version = models.IntegerField(default=0)
    version_comment = models.TextField(null=True)
    old_panels = ArrayField(models.CharField(max_length=255))

    @cached_property
    def stats(self):
        return self.genepanelentrysnapshot_set.aggregate(
            number_of_reviewers=Count('evaluation__user', distinct=True),
            number_of_evaluated_genes=Count('evaluation'),
            number_of_genes=Count('pk'),
            number_of_ready_genes=Sum(Case(When(
                ready=True, then=Value(1)),
                default=Value(0),
                output_field=IntegerField()
            )),
            number_of_green_genes=Sum(Case(When(
                saved_gel_status__gte=3, then=Value(1)),
                default=Value(0),
                output_field=IntegerField()
            ))
        )

    def __str__(self):
        return "Panel {} v{}.{}".format(self.level4title.name, self.major_version, self.minor_version)

    def increment_version(self, major=False):
        current_genes = self.get_all_entries

        self.pk = None

        if major:
            self.major_version += 1
            self.minor_version = 0
        else:
            self.minor_version += 1

        self.save()

        for gene in current_genes:
            evidences = gene.evidence.all()
            evaluations = gene.evaluation.all()
            tracks = gene.track.all()
            tags = gene.tags.all()
            comments = gene.comments.all()

            gene.pk = None
            gene.panel = self
            gene.save()

            for evidence in evidences:
                gene.evidence.add(evidence)

            for evaluation in evaluations:
                gene.evaluation.add(evaluation)

            for track in tracks:
                gene.track.add(track)

            for tag in tags:
                gene.tag.add(tag)

            for comment in comments:
                gene.comments.add(comment)

    def mark_genes_not_ready(self):
        for gene in self.genepanelentrysnapshot_set.all():
            gene.ready = False
            gene.save()

    def get_form_initial(self):
        return {
            "level4": self.level4title.name,
            "level2": self.level4title.level2title,
            "level3": self.level4title.level3title,
            "description": self.level4title.description,
            "omim": ", ".join(self.level4title.omim),
            "orphanet": ", ".join(self.level4title.orphanet),
            "hpo": ", ".join(self.level4title.hpo),
            "old_panels": ", ".join(self.old_panels)
        }

    @cached_property
    def get_all_entries(self):
        return self.genepanelentrysnapshot_set\
            .distinct('gene_core__gene_symbol')\
            .prefetch_related('evidence', 'evaluation', 'tags')\
            .order_by('gene_core__gene_symbol', '-created')\
            .all()

    def get_gene(self, gene_symbol):
        return self.get_all_entries.filter(gene__gene_symbol=gene_symbol).first()

    def has_gene(self, gene_symbol):
        return True if self.get_all_entries.filter(gene__gene_symbol=gene_symbol).count() > 0 else False

    def delete_gene(self, gene_symbol, increment=True):
        """
        Removes gene from a panel, but leaves it in the previous versions of the same panel
        """

        if self.has_gene(gene_symbol):
            if increment:
                self.increment_version()
            del self.get_all_entries  # clear cached values as it points to the previous instance
            self.get_all_entries.get(gene__gene_symbol=gene_symbol).delete()
            del self.get_all_entries  # clear cached values as we deleted item

    """
    # move these to properties
    number_of_green_rating = models.IntegerField(null=True,  blank=True,)
    number_of_red_rating = models.IntegerField(null=True,  blank=True,)
    number_of_amber_rating = models.IntegerField(null=True,  blank=True,)
    """
