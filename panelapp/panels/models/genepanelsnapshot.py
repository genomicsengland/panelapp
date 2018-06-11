import logging
from copy import deepcopy
from django.db import models
from django.db import transaction
from django.db.models import Count
from django.db.models import Case
from django.db.models import When
from django.db.models import Subquery
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.aggregates import ArrayAgg
from django.utils.functional import cached_property
from model_utils.models import TimeStampedModel

from panels.tasks import email_panel_promoted
from .activity import Activity
from .genepanel import GenePanel
from .Level4Title import Level4Title
from .trackrecord import TrackRecord
from .evidence import Evidence
from .evaluation import Evaluation
from .gene import Gene
from .comment import Comment
from .tag import Tag


class GenePanelSnapshotManager(models.Manager):
    def get_latest_ids(self, deleted=False):
        """Get latest versions for GenePanelsSnapshots"""

        qs = super().get_queryset()
        if not deleted:
            qs = qs.exclude(panel__status=GenePanel.STATUS.deleted)

        return qs\
            .distinct('panel__pk')\
            .values('pk')\
            .order_by('panel__pk', '-major_version', '-minor_version')

    def get_active(self, all=False, deleted=False, internal=False):
        """Get active panels

        Parameters:
            - all
                Setting it to False will only return `public` panels
            - deleted
                Whether to include the deleted panels
            - internal
                If we want to include `internal` panels in the list
        """

        qs = super().get_queryset()

        if not all:
            qs = qs.filter(Q(panel__status=GenePanel.STATUS.public) | Q(panel__status=GenePanel.STATUS.promoted))

        if not internal:
            qs = qs.exclude(panel__status=GenePanel.STATUS.internal)

        return qs.filter(pk__in=Subquery(self.get_latest_ids(deleted)))\
            .prefetch_related('panel', 'level4title')\
            .order_by('panel__name', '-major_version', '-minor_version')

    def get_active_annotated(self, all=False, deleted=False, internal=False):
        """This method adds additional values to the queryset, such as number_of_genes, etc and returns active panels"""

        return self.get_active(all, deleted, internal)

    def get_gene_panels(self, gene_symbol, all=False, internal=False):
        """Get all panels for a specific gene in Gene entities"""

        return self.get_active_annotated(all=all, internal=internal).filter(genepanelentrysnapshot__gene__gene_symbol=gene_symbol)

    def get_strs_panels(self, gene_symbol, all=False, internal=False):
        """Get all panels for a specific gene in STR entities"""

        return self.get_active_annotated(all=all, internal=internal).filter(strs_gene__gene_symbol=gene_symbol)

    def get_shared_panels(self, gene_symbol, all=False, internal=False):
        """Get all panels for a specific gene"""

        qs = self.get_active(all=all, internal=internal)
        qs = qs.filter(genepanelentrysnapshot__gene_core__gene_symbol=gene_symbol)\
            .union(qs.filter(str__gene_core__gene_symbol=gene_symbol))
        return qs


class GenePanelSnapshot(TimeStampedModel):
    """Main Gene Panel model

    GenePanel is just a placeholder with a static ID for a panel, all
    information for the genes is actually stored in GenePanelSnapshot.

    Every time we change something in a gene or in a panel we create a new
    spanshot and make the changes there. This allows us to preserve the changes
    between versions and we can retrieve a specific version.
    """
    class Meta:
        get_latest_by = "created"
        ordering = ['-major_version', '-minor_version', ]
        indexes = [
            models.Index(fields=['panel_id']),
        ]

    objects = GenePanelSnapshotManager()

    level4title = models.ForeignKey(Level4Title)
    panel = models.ForeignKey(GenePanel)
    major_version = models.IntegerField(default=0, db_index=True)
    minor_version = models.IntegerField(default=0, db_index=True)
    version_comment = models.TextField(null=True)
    old_panels = ArrayField(models.CharField(max_length=255), blank=True, null=True)

    current_number_of_reviewers = models.IntegerField(null=True, blank=True)
    current_number_of_evaluated_genes = models.IntegerField(null=True, blank=True)
    current_number_of_genes = models.IntegerField(null=True, blank=True)
    current_number_of_evaluated_strs = models.IntegerField(null=True, blank=True)
    current_number_of_strs = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return "{} v{}.{}".format(self.level4title.name, self.major_version, self.minor_version)

    def get_absolute_url(self):
        return reverse('panels:detail', args=(self.panel.pk,))

    @cached_property
    def stats(self):
        """Get stats for a panel, i.e. number of reviewers, genes, evaluated genes, etc"""

        return GenePanelSnapshot.objects.filter(pk=self.pk).aggregate(
            number_of_gene_reviewers=Count('genepanelentrysnapshot__evaluation__user__pk', distinct=True),
            number_of_str_reviewers=Count('str__evaluation__user__pk', distinct=True),
            number_of_evaluated_genes=Count(Case(
                # Count unique genes if that gene has more than 1 evaluation
                When(
                    genepanelentrysnapshot__evaluation__isnull=False,
                    then=models.F('genepanelentrysnapshot__pk')
                )
            ), distinct=True),
            number_of_genes=Count('genepanelentrysnapshot__pk', distinct=True),
            number_of_ready_genes=Count(
                Case(
                    When(
                        genepanelentrysnapshot__ready=True,
                        then=models.F('genepanelentrysnapshot__pk')
                    )
                ),
                distinct=True
            ),
            number_of_green_genes=Count(
                Case(
                    When(
                        genepanelentrysnapshot__saved_gel_status__gte=3,
                        then=models.F('genepanelentrysnapshot__pk')
                    )
                ),
                distinct=True
            ),
            number_of_evaluated_strs=Count(Case(
                # Count unique genes if that gene has more than 1 evaluation
                When(
                    str__evaluation__isnull=False,
                    then=models.F('str__pk')
                )
            ), distinct=True),
            number_of_strs=Count('str__pk', distinct=True),
            number_of_ready_strs=Count(
                Case(
                    When(
                        str__ready=True,
                        then=models.F('str__pk')
                    )
                ),
                distinct=True
            ),
            number_of_green_strs=Count(
                Case(
                    When(
                        str__saved_gel_status__gte=3,
                        then=models.F('str__pk')
                    )
                ),
                distinct=True
            ),
        )

    @property
    def number_of_reviewers(self):
        """Get number of reviewers or set it if it's None"""

        if self.current_number_of_reviewers is None:
            self.update_saved_stats()
        return self.current_number_of_reviewers

    @property
    def number_of_evaluated_genes(self):
        """Get number of evaluated genes or set it if it's None"""

        if self.current_number_of_evaluated_genes is None:
            self.update_saved_stats()
        return self.current_number_of_evaluated_genes

    @property
    def number_of_genes(self):
        """Get number of genes or set it if it's None"""

        if self.current_number_of_genes is None:
            self.update_saved_stats()
        return self.current_number_of_genes

    @property
    def number_of_evaluated_strs(self):
        """Get number of evaluated genes or set it if it's None"""

        if self.current_number_of_evaluated_strs is None:
            self.update_saved_stats()
        return self.current_number_of_evaluated_strs

    @property
    def number_of_strs(self):
        """Get number of genes or set it if it's None"""

        if self.current_number_of_strs is None:
            self.update_saved_stats()
        return self.current_number_of_strs

    @property
    def version(self):
        return "{}.{}".format(self.major_version, self.minor_version)

    def increment_version(self, major=False, user=None, comment=None, ignore_gene=None, ignore_str=None):
        """Creates a new version of the panel.

        This script copies all genes, all information for these genes, and also
        you can add a comment and a user if it's a major version increment.

        DO NOT use it inside the methods of either genes or GenePanelSnapshot.
        This has weird behaviour as self references still goes to the previous
        snapshot and not the new one.
        """

        with transaction.atomic():
            current_genes = deepcopy(self.get_all_genes)  # cache the results
            current_strs = deepcopy(self.get_all_strs)

            self.pk = None

            if major:
                self.major_version += 1
                self.minor_version = 0
            else:
                self.minor_version += 1

            self.save()

            self._increment_version_genes(current_genes, major, user, comment, ignore_gene)
            self._increment_version_str(current_strs, major, user, comment, ignore_str)

            if major:
                email_panel_promoted.delay(self.panel.pk)

                activity = "promoted panel to version {}".format(self.version)
                self.add_activity(user, activity)

                self.version_comment = "{} {} promoted panel to {}\n{}\n\n{}".format(
                    timezone.now().strftime('%Y-%m-%d %H:%M'),
                    user.get_reviewer_name(),
                    self.version,
                    comment,
                    self.version_comment if self.version_comment else ''
                )
                self.save()

            return self.panel.active_panel

    def _increment_version_genes(self, current_genes, major, user, comment, ignore_gene):
        evidences = []
        evaluations = []
        tracks = []
        tags = []
        comments = []

        genes = {}

        for gene in current_genes:
            if ignore_gene and ignore_gene == gene.gene.get('gene_symbol'):
                continue

            old_gene = deepcopy(gene)
            gene.pk = None
            gene.panel = self

            if major:
                gene.ready = False
                gene.save()

            genes[gene.gene.get('gene_symbol')] = {
                'gene': gene,
                'old_gene': old_gene,
                'evidences': [
                    {
                        'evidence_id': ev,
                        'genepanelentrysnapshot_id': gene.pk
                    } for ev in set(gene.evidences) if ev is not None
                ],
                'evaluations': [
                    {
                        'evaluation_id': ev,
                        'genepanelentrysnapshot_id': gene.pk
                    } for ev in set(gene.evaluations) if ev is not None
                ],
                'tracks': [
                    {
                        'trackrecord_id': ev,
                        'genepanelentrysnapshot_id': gene.pk
                    } for ev in set(gene.tracks) if ev is not None
                ],
                'tags': [
                    {
                        'tag_id': ev,
                        'genepanelentrysnapshot_id': gene.pk
                    } for ev in set(gene.gene_tags) if ev is not None
                ],
                'comments': [
                    {
                        'comment_id': ev,
                        'genepanelentrysnapshot_id': gene.pk
                    } for ev in set(gene.comment_pks) if ev is not None
                ]
            }

            if major and user and comment:
                issue_type = "Panel promoted to version {}".format(self.version)
                issue_description = comment

                track_promoted = TrackRecord.objects.create(
                    curator_status=user.reviewer.is_GEL(),
                    issue_description=issue_description,
                    gel_status=gene.status,
                    issue_type=issue_type,
                    user=user
                )
                gene.track.add(track_promoted)

        # add in bulk
        if not major:
            bulk_genes = [genes[gene]['gene'] for gene in genes]
            new_genes = self.genepanelentrysnapshot_set.model.objects.bulk_create(bulk_genes)
        else:
            new_genes = self.genepanelentrysnapshot_set.all()

        self.clear_cache()

        for gene in new_genes:
            gene_data = genes[gene.gene.get('gene_symbol')]

            for i, _ in enumerate(gene_data['evidences']):
                gene_data['evidences'][i]['genepanelentrysnapshot_id'] = gene_data['gene'].pk
            evidences.extend(gene_data['evidences'])

            for i, _ in enumerate(gene_data['evaluations']):
                gene_data['evaluations'][i]['genepanelentrysnapshot_id'] = gene_data['gene'].pk
            evaluations.extend(gene_data['evaluations'])

            for i, _ in enumerate(gene_data['tracks']):
                gene_data['tracks'][i]['genepanelentrysnapshot_id'] = gene_data['gene'].pk
            tracks.extend(gene_data['tracks'])

            for i, _ in enumerate(gene_data['tags']):
                gene_data['tags'][i]['genepanelentrysnapshot_id'] = gene_data['gene'].pk
            tags.extend(gene_data['tags'])

            for i, _ in enumerate(gene_data['comments']):
                gene_data['comments'][i]['genepanelentrysnapshot_id'] = gene_data['gene'].pk
            comments.extend(gene_data['comments'])

        self.genepanelentrysnapshot_set.model.evidence.through.objects.bulk_create([
            self.genepanelentrysnapshot_set.model.evidence.through(**ev) for ev in evidences
        ])
        self.genepanelentrysnapshot_set.model.evaluation.through.objects.bulk_create([
            self.genepanelentrysnapshot_set.model.evaluation.through(**ev) for ev in evaluations
        ])
        self.genepanelentrysnapshot_set.model.track.through.objects.bulk_create([
            self.genepanelentrysnapshot_set.model.track.through(**ev) for ev in tracks
        ])
        self.genepanelentrysnapshot_set.model.tags.through.objects.bulk_create([
            self.genepanelentrysnapshot_set.model.tags.through(**ev) for ev in tags
        ])
        self.genepanelentrysnapshot_set.model.comments.through.objects.bulk_create([
            self.genepanelentrysnapshot_set.model.comments.through(**ev) for ev in comments
        ])

    def _increment_version_str(self, current_strs, major, user, comment, ignore_str):
        evidences = []
        evaluations = []
        tracks = []
        tags = []
        comments = []

        strs = {}

        for str_entity in current_strs:
            if ignore_str and ignore_str == str_entity.name:
                continue

            old_str = deepcopy(str_entity)
            str_entity.pk = None
            str_entity.panel = self

            if major:
                str_entity.ready = False
                str_entity.save()

            strs[str_entity.name] = {
                'str': str_entity,
                'old_str': old_str,
                'evidences': [
                    {
                        'evidence_id': ev,
                        'str_id': str_entity.pk
                    } for ev in set(str_entity.evidences) if ev is not None
                ],
                'evaluations': [
                    {
                        'evaluation_id': ev,
                        'str_id': str_entity.pk
                    } for ev in set(str_entity.evaluations) if ev is not None
                ],
                'tracks': [
                    {
                        'trackrecord_id': ev,
                        'str_id': str_entity.pk
                    } for ev in set(str_entity.tracks) if ev is not None
                ],
                'tags': [
                    {
                        'tag_id': ev,
                        'str_id': str_entity.pk
                    } for ev in set(str_entity.gene_tags) if ev is not None
                ],
                'comments': [
                    {
                        'comment_id': ev,
                        'str_id': str_entity.pk
                    } for ev in set(str_entity.comment_pks) if ev is not None
                ]
            }

            if major and user and comment:
                issue_type = "Panel promoted to version {}".format(self.version)
                issue_description = comment

                track_promoted = TrackRecord.objects.create(
                    curator_status=user.reviewer.is_GEL(),
                    issue_description=issue_description,
                    gel_status=str_entity.status,
                    issue_type=issue_type,
                    user=user
                )
                str_entity.track.add(track_promoted)

        # add in bulk
        if not major:
            bulk_strs = [strs[str_entity]['str'] for str_entity in strs]
            new_strs = self.str_set.model.objects.bulk_create(bulk_strs)
        else:
            new_strs = self.str_set.all()

        self.clear_cache()

        for str_entity in new_strs:
            str_data = strs[str_entity.name]

            for i, _ in enumerate(str_data['evidences']):
                str_data['evidences'][i]['str_id'] = str_data['str'].pk
            evidences.extend(str_data['evidences'])

            for i, _ in enumerate(str_data['evaluations']):
                str_data['evaluations'][i]['str_id'] = str_data['str'].pk
            evaluations.extend(str_data['evaluations'])

            for i, _ in enumerate(str_data['tracks']):
                str_data['tracks'][i]['str_id'] = str_data['str'].pk
            tracks.extend(str_data['tracks'])

            for i, _ in enumerate(str_data['tags']):
                str_data['tags'][i]['str_id'] = str_data['str'].pk
            tags.extend(str_data['tags'])

            for i, _ in enumerate(str_data['comments']):
                str_data['comments'][i]['str_id'] = str_data['str'].pk
            comments.extend(str_data['comments'])

        self.str_set.model.evidence.through.objects.bulk_create([
            self.str_set.model.evidence.through(**ev) for ev in evidences
        ])
        self.str_set.model.evaluation.through.objects.bulk_create([
            self.str_set.model.evaluation.through(**ev) for ev in evaluations
        ])
        self.str_set.model.track.through.objects.bulk_create([
            self.str_set.model.track.through(**ev) for ev in tracks
        ])
        self.str_set.model.tags.through.objects.bulk_create([
            self.str_set.model.tags.through(**ev) for ev in tags
        ])
        self.str_set.model.comments.through.objects.bulk_create([
            self.str_set.model.comments.through(**ev) for ev in comments
        ])

    def update_saved_stats(self):
        """Get the new values from the database"""

        if self.stats:
            del self.stats

        self.current_number_of_reviewers = self.stats.get('number_of_gene_reviewers', 0)
        self.current_number_of_evaluated_genes = self.stats.get('number_of_evaluated_genes', 0)
        self.current_number_of_genes = self.stats.get('number_of_genes', 0)
        self.current_number_of_evaluated_strs = self.stats.get('number_of_evaluated_strs', 0)
        self.current_number_of_strs = self.stats.get('number_of_strs', 0)
        self.save(update_fields=[
            'current_number_of_evaluated_genes',
            'current_number_of_reviewers',
            'current_number_of_genes',
            'current_number_of_evaluated_strs',
            'current_number_of_strs',
        ])

    @property
    def contributors(self):
        """Returns a tuple with user data

        Returns:
            A tuple with the user first and last name, email, and reviewer affiliation
        """

        return self.cached_genes\
            .distinct('evaluation__user')\
            .values_list(
                'evaluation__user__first_name',
                'evaluation__user__last_name',
                'evaluation__user__email',
                'evaluation__user__reviewer__affiliation',
                'evaluation__user__username'
            ).order_by('evaluation__user')

    def mark_entities_not_ready(self):
        """Mark entities (genes, STRs) as not ready

        @TODO(Oleg) refactor this method at some point, and run it as a single query per entity

        Returns:
             None
        """
        for gene in self.cached_genes.all():
            gene.ready = False
            gene.save()

        for str_item in self.cached_strs.all():
            str_item.ready = False
            str_item.save()

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
    def cached_genes(self):
        return self.genepanelentrysnapshot_set.all()

    @cached_property
    def cached_strs(self):
        return self.str_set.all()

    @cached_property
    def current_genes(self):
        """Select and cache gene names"""
        return list(self.current_genes_count.keys())

    @cached_property
    def current_genes_count(self):
        genes_list = [g.get('gene_symbol') for g in self.cached_genes.values_list('gene', flat=True)]
        return {gene: genes_list.count(gene) for gene in genes_list if gene}

    @cached_property
    def current_genes_duplicates(self):
        return [gene for gene in self.current_genes_count if self.current_genes_count[gene] > 1]

    @cached_property
    def get_all_genes(self):
        """Returns all Genes for this panel"""

        return self.cached_genes\
            .annotate(
                evidences=ArrayAgg('evidence__pk', distinct=True),
                evaluations=ArrayAgg('evaluation__pk', distinct=True),
                gene_tags=ArrayAgg('tags__pk', distinct=True),
                tracks=ArrayAgg('track__pk', distinct=True),
                comment_pks=ArrayAgg('comments__pk', distinct=True)
            )

    @cached_property
    def get_all_strs(self):
        """Returns all Genes for this panel"""

        return self.cached_strs.annotate(
            evidences=ArrayAgg('evidence__pk', distinct=True),
            evaluations=ArrayAgg('evaluation__pk', distinct=True),
            gene_tags=ArrayAgg('tags__pk', distinct=True),
            tracks=ArrayAgg('track__pk', distinct=True),
            comment_pks=ArrayAgg('comments__pk', distinct=True)
        )

    @cached_property
    def get_all_genes_extra(self):
        """Get all genes and annotated info, speeds up loading time"""

        return self.cached_genes\
            .prefetch_related(
                'evidence',
                'evidence__reviewer',
                'evaluation',
                'evaluation__user',
                'evaluation__user__reviewer',
                'tags'
            )\
            .annotate(
                number_of_green_evaluations=Count(Case(When(
                    evaluation__rating="GREEN", then=models.F('evaluation__pk'))
                ), distinct=True),
                number_of_red_evaluations=Count(Case(When(
                    evaluation__rating="RED", then=models.F('evaluation__pk'))
                ), distinct=True),
                evaluators=ArrayAgg('evaluation__user__pk'),
                number_of_evaluations=Count('evaluation__pk', distinct=True)
            )\
            .order_by('-saved_gel_status', 'gene_core__gene_symbol')

    @cached_property
    def get_all_strs_extra(self):
        """Get all genes and annotated info, speeds up loading time"""

        return self.cached_strs.prefetch_related(
            'evidence',
            'evidence__reviewer',
            'evaluation',
            'evaluation__user',
            'evaluation__user__reviewer',
            'tags'
        ).annotate(
            number_of_green_evaluations=Count(Case(When(
                evaluation__rating="GREEN", then=models.F('evaluation__pk'))
            ), distinct=True),
            number_of_red_evaluations=Count(Case(When(
                evaluation__rating="RED", then=models.F('evaluation__pk'))
            ), distinct=True),
            evaluators=ArrayAgg('evaluation__user__pk'),
            number_of_evaluations=Count('evaluation__pk', distinct=True)
        ).order_by('-saved_gel_status', 'name')
    
    def get_gene_by_pk(self, gene_pk, prefetch_extra=False):
        """Get a gene for a specific pk."""

        if prefetch_extra:
            return self.get_all_genes_extra.prefetch_related(
                'evaluation__comments',
                'evaluation__user__reviewer',
                'track',
                'track__user',
                'track__user__reviewer'
            ).get(pk=gene_pk)
        else:
            return self.get_all_genes.get(pk=gene_pk)

    def get_gene(self, gene_symbol, prefetch_extra=False):
        """Get a gene for a specific gene symbol."""

        if prefetch_extra:
            return self.get_all_genes_extra.prefetch_related(
                'evaluation__comments',
                'evaluation__user__reviewer',
                'track',
                'track__user',
                'track__user__reviewer'
            ).get(gene__gene_symbol=gene_symbol)
        else:
            return self.get_all_genes.get(gene__gene_symbol=gene_symbol)

    def has_gene(self, gene_symbol):
        """Check if the panel has a gene with the provided gene symbol"""

        return gene_symbol in [
            symbol.get('gene_symbol') for symbol in self.genepanelentrysnapshot_set.values_list('gene', flat=True)
        ]

    def get_str(self, name, prefetch_extra=False):
        """Get a STR."""

        if prefetch_extra:
            return self.get_all_strs_extra.prefetch_related(
                'evaluation__comments',
                'evaluation__user__reviewer',
                'track',
                'track__user',
                'track__user__reviewer'
            ).get(name=name)
        else:
            return self.get_all_strs.get(name=name)

    def has_str(self, str_name):
        return self.str_set.filter(name=str_name).count() > 0

    def clear_cache(self):
        if self.__dict__.get('cached_genes'):
            del self.__dict__['cached_genes']
        if self.__dict__.get('cached_strs'):
            del self.__dict__['cached_strs']
        if self.__dict__.get('current_genes_count'):
            del self.__dict__['current_genes_count']
        if self.__dict__.get('current_genes_duplicates'):
            del self.__dict__['current_genes_duplicates']
        if self.__dict__.get('current_genes'):
            del self.__dict__['current_genes']
        if self.__dict__.get('get_all_genes'):
            del self.__dict__['get_all_genes']
        if self.__dict__.get('get_all_genes_extra'):
            del self.__dict__['get_all_genes_extra']
        if self.__dict__.get('get_all_strs'):
            del self.__dict__['get_all_strs']
        if self.__dict__.get('get_all_strs_extra'):
            del self.__dict__['get_all_strs_extra']

    def delete_gene(self, gene_symbol, increment=True, user=None):
        """Removes gene from a panel, but leaves it in the previous versions of the same panel"""

        if self.has_gene(gene_symbol):
            if increment:
                self = self.increment_version(ignore_gene=gene_symbol)
            else:
                self.get_all_genes.get(gene__gene_symbol=gene_symbol).delete()
                self.clear_cache()

            if user:
                self.add_activity(user, "removed gene:{} from the panel".format(gene_symbol))

            self.update_saved_stats()
            return True
        else:
            return False

    def delete_str(self, str_name, increment=True, user=None):
        """Removes STR from a panel, but leaves it in the previous versions of the same panel"""

        if self.has_str(str_name):
            if increment:
                self = self.increment_version(ignore_str=str_name)
            else:
                self.cached_strs.get(name=str_name).delete()
                self.clear_cache()

            if user:
                self.add_activity(user, "removed STR:{} from the panel".format(str_name))

            self.update_saved_stats()
            return True
        else:
            return False

    def add_gene(self, user, gene_symbol, gene_data, increment_version=True):
        """Adds a new gene to the panel

        Args:
            user: User instance. It's the user who is adding a new gene, we need
                this info to add to TrackRecord, Activities, Evidence, and Evaluation
            gene_symbol: Gene symbol string
            gene_data: A dict with the values:
                - moi
                - penetrance
                - publications
                - phenotypes
                - mode_of_pathogenicity
                - comment
                - current_diagnostic
                - sources
                - rating
                - tags

        Returns:
            GenePanelEntrySnapshot instance of a freshly created Gene in a Panel.
            Or False in case the gene is already in the panel.
        """

        if self.has_gene(gene_symbol):
            return False

        if increment_version:
            self = self.increment_version()

        gene_core = Gene.objects.get(gene_symbol=gene_symbol)
        gene_info = gene_core.dict_tr()

        gene = self.cached_genes.model(
            gene=gene_info,
            panel=self,
            gene_core=gene_core,
            moi=gene_data.get('moi'),
            penetrance=gene_data.get('penetrance'),
            publications=gene_data.get('publications'),
            phenotypes=gene_data.get('phenotypes'),
            mode_of_pathogenicity=gene_data.get('mode_of_pathogenicity'),
            saved_gel_status=0,
            flagged=False if user.reviewer.is_GEL() else True
        )
        gene.save()

        for source in gene_data.get('sources'):
            evidence = Evidence.objects.create(
                rating=5,
                reviewer=user.reviewer,
                name=source.strip()
            )
            gene.evidence.add(evidence)

        tracks = []
        evidence_status = gene.evidence_status()
        tracks.append((
            TrackRecord.ISSUE_TYPES.Created,
            "{} was added by {}".format(gene_core.gene_symbol, user.get_full_name())
        ))

        for tag in gene_data.get('tags', []):
            gene.tags.add(tag)

            description = "{} was added to {}.".format(
                tag,
                gene_symbol
            )
            tracks.append((
                TrackRecord.ISSUE_TYPES.AddedTag,
                description
            ))

        description = "{} was added to {}. Sources: {}".format(
            gene_core.gene_symbol,
            self.panel.name,
            ",".join(gene_data.get('sources'))
        )
        tracks.append((
            TrackRecord.ISSUE_TYPES.NewSource,
            description
        ))

        if gene_symbol.startswith("MT-"):
            gene.moi = "MITOCHONDRIAL"
            description = "Model of inheritance for gene {} was set to {}".format(
                gene_symbol,
                "MITOCHONDRIAL"
            )
            tracks.append((
                TrackRecord.ISSUE_TYPES.SetModeofInheritance,
                description
            ))

        if gene_data.get('rating') or gene_data.get('comment') or gene_data.get('source'):
            evaluation = Evaluation.objects.create(
                user=user,
                rating=gene_data.get('rating'),
                mode_of_pathogenicity=gene_data.get('mode_of_pathogenicity'),
                phenotypes=gene_data.get('phenotypes'),
                publications=gene_data.get('publications'),
                moi=gene_data.get('moi'),
                current_diagnostic=gene_data.get('current_diagnostic'),
                version=self.version
            )
            comment_text = gene_data.get('comment', '')
            sources = ', '.join(gene_data.get('sources', []))
            if sources and comment_text:
                comment_text = comment_text + ' \nSources: ' + sources
            else:
                comment_text = 'Sources: ' + sources
            comment = Comment.objects.create(
                user=user,
                comment=comment_text
            )
            if gene_data.get('comment') or gene_data.get('sources', []):
                evaluation.comments.add(comment)
            gene.evaluation.add(evaluation)
        self.clear_cache()

        if tracks:
            description = "\n".join([t[1] for t in tracks])
            track = TrackRecord.objects.create(
                gel_status=evidence_status,
                curator_status=0,
                user=user,
                issue_type=",".join([t[0] for t in tracks]),
                issue_description=description
            )
            gene.track.add(track)
            self.add_activity(user, description, gene)

        gene.evidence_status(update=True)
        self.update_saved_stats()
        return gene

    def update_gene(self, user, gene_symbol, gene_data, append_only=False):
        """Updates a gene if it exists in this panel

        Args:
            user: User instance. It's the user who is updating a gene, we need
                this info to add to TrackRecord, Activities, Evidence, and Evaluation
            gene_symbol: Gene symbol string
            gene_data: A dict with the values:
                - moi
                - penetrance
                - publications
                - phenotypes
                - mode_of_pathogenicity
                - comment
                - current_diagnostic
                - sources
                - rating
                - gene

                if `gene` is in the gene_data and it's different to the stored gene
                it will change the gene data, and remove the old gene from the panel.

        Returns:
            GenePanelEntrySnapshot if the gene was successfully updated, False otherwise
        """

        logging.debug("Updating gene:{} panel:{} gene_data:{}".format(gene_symbol, self, gene_data))
        has_gene = self.has_gene(gene_symbol=gene_symbol)
        if has_gene:
            logging.debug("Found gene:{} in panel:{}. Incrementing version.".format(gene_symbol, self))
            gene = self.get_gene(gene_symbol=gene_symbol)

            if gene_data.get('flagged') is not None:
                gene.flagged = gene_data.get('flagged')

            tracks = []
            evidences_names = [ev.strip() for ev in gene.evidence.values_list('name', flat=True)]

            logging.debug("Updating evidences_names for gene:{} in panel:{}".format(gene_symbol, self))
            if gene_data.get('sources'):
                add_evidences = [
                    source.strip() for source in gene_data.get('sources')
                    if source not in evidences_names
                ]

                has_expert_review = any([evidence in Evidence.EXPERT_REVIEWS for evidence in add_evidences])

                delete_evidences = [
                    source for source in evidences_names
                    if (has_expert_review or source not in Evidence.EXPERT_REVIEWS)
                    and source not in gene_data.get('sources')
                ]

                if append_only and has_expert_review:
                    # just remove expert review
                    expert_reviews = [source for source in evidences_names if source in Evidence.EXPERT_REVIEWS]
                    for expert_review in expert_reviews:
                        ev = gene.evidence.filter(name=expert_review).first()
                        gene.evidence.remove(ev)
                elif not append_only:
                    for source in delete_evidences:
                        ev = gene.evidence.filter(name=source).first()
                        gene.evidence.remove(ev)
                        logging.debug("Removing evidence:{} for gene:{} panel:{}".format(
                            source, gene_symbol, self
                        ))
                        description = "Source {} was removed from {}. Panel: {}".format(
                            source,
                            gene_symbol,
                            self.panel.name
                        )
                        tracks.append((
                            TrackRecord.ISSUE_TYPES.RemovedSource,
                            description
                        ))

                for source in add_evidences:
                    logging.debug("Adding new evidence:{} for gene:{} panel:{}".format(
                        source, gene_symbol, self
                    ))
                    evidence = Evidence.objects.create(
                        name=source,
                        rating=5,
                        reviewer=user.reviewer
                    )
                    gene.evidence.add(evidence)

                    description = "{} was added to {}. Panel: {}".format(
                        source,
                        gene_symbol,
                        self.panel.name,
                    )
                    tracks.append((
                        TrackRecord.ISSUE_TYPES.NewSource,
                        description
                    ))

            moi = gene_data.get('moi')
            if moi and gene.moi != moi and not gene_symbol.startswith("MT-"):
                logging.debug("Updating moi for gene:{} in panel:{}".format(gene_symbol, self))
                gene.moi = moi

                description = "Model of inheritance for gene {} was set to {}".format(
                    gene_symbol,
                    moi
                )
                tracks.append((
                    TrackRecord.ISSUE_TYPES.SetModeofInheritance,
                    description
                ))
            elif gene_symbol.startswith("MT-") and gene.moi != 'MITOCHONDRIAL':
                logging.debug("Updating moi for gene:{} in panel:{}".format(gene_symbol, self))
                gene.moi = "MITOCHONDRIAL"
                description = "Model of inheritance for gene {} was set to {}".format(
                    gene_symbol,
                    "MITOCHONDRIAL"
                )
                tracks.append((
                    TrackRecord.ISSUE_TYPES.SetModeofInheritance,
                    description
                ))

            mop = gene_data.get('mode_of_pathogenicity')
            if mop and gene.mode_of_pathogenicity != mop:
                logging.debug("Updating mop for gene:{} in panel:{}".format(gene_symbol, self))
                gene.mode_of_pathogenicity = mop

                description = "Model of pathogenicity for gene {} was set to {}".format(
                    gene_symbol,
                    mop
                )
                tracks.append((
                    TrackRecord.ISSUE_TYPES.SetModeofPathogenicity,
                    description
                ))

            phenotypes = gene_data.get('phenotypes')
            if phenotypes:
                current_phenotypes = [ph.strip() for ph in gene.phenotypes]

                add_phenotypes = [
                    phenotype.strip() for phenotype in phenotypes
                    if phenotype not in current_phenotypes
                ]

                delete_phenotypes = [
                    phenotype.strip() for phenotype in current_phenotypes
                    if phenotype not in phenotypes
                ]

                logging.debug("Updating phenotypes for gene:{} in panel:{}".format(gene_symbol, self))

                if not append_only:
                    for phenotype in delete_phenotypes:
                        current_phenotypes.remove(phenotype)

                for phenotype in add_phenotypes:
                    current_phenotypes.append(phenotype)

                gene.phenotypes = current_phenotypes

                description = "Phenotypes for gene {} were set to {}".format(
                    gene_symbol,
                    ', '.join(current_phenotypes)
                )
                tracks.append((
                    TrackRecord.ISSUE_TYPES.SetPenetrance,
                    description
                ))

            penetrance = gene_data.get('penetrance')
            if penetrance and gene.penetrance != penetrance:
                gene.penetrance = penetrance
                logging.debug("Updating penetrance for gene:{} in panel:{}".format(gene_symbol, self))
                description = "Penetrance for gene {} was set to {}".format(
                    gene_symbol,
                    penetrance
                )
                tracks.append((
                    TrackRecord.ISSUE_TYPES.SetPenetrance,
                    description
                ))

            publications = gene_data.get('publications')
            if publications and gene.publications != publications:
                gene.publications = publications
                logging.debug("Updating publications for gene:{} in panel:{}".format(gene_symbol, self))
                description = "Publications for gene {} was set to {}".format(
                    gene_symbol,
                    publications
                )
                tracks.append((
                    TrackRecord.ISSUE_TYPES.SetPublications,
                    description
                ))

            current_tags = [tag.pk for tag in gene.tags.all()]
            tags = gene_data.get('tags')
            if tags or current_tags:
                if not tags:
                    tags = []

                new_tags = [tag.pk for tag in tags]
                add_tags = [
                    tag for tag in tags
                    if tag.pk not in current_tags
                ]
                delete_tags = [
                    tag for tag in current_tags
                    if tag not in new_tags
                ]

                if not append_only:
                    for tag in delete_tags:
                        tag = gene.tags.get(pk=tag)
                        gene.tags.remove(tag)
                        logging.debug("Removing tag:{} for gene:{} panel:{}".format(
                            tag.name, gene_symbol, self
                        ))
                        description = "{} was removed from {}. Panel: {}".format(
                            tag,
                            gene_symbol,
                            self.panel.name,
                        )
                        tracks.append((
                            TrackRecord.ISSUE_TYPES.RemovedTag,
                            description
                        ))

                for tag in add_tags:
                    logging.debug("Adding new tag:{} for gene:{} panel:{}".format(
                        tag, gene_symbol, self
                    ))
                    gene.tags.add(tag)

                    description = "{} was added to {}. Panel: {}".format(
                        tag,
                        gene_symbol,
                        self.panel.name,
                    )
                    tracks.append((
                        TrackRecord.ISSUE_TYPES.AddedTag,
                        description
                    ))

            if tracks:
                logging.debug("Adding tracks for gene:{} in panel:{}".format(gene_symbol, self))
                status = gene.evidence_status(True)
                description = "\n".join([t[1] for t in tracks])
                track = TrackRecord.objects.create(
                    gel_status=status,
                    curator_status=0,
                    user=user,
                    issue_type=",".join([t[0] for t in tracks]),
                    issue_description=description
                )
                gene.track.add(track)
                self.add_activity(user, description, gene)

            new_gene = gene_data.get('gene')
            gene_name = gene_data.get('gene_name')

            if new_gene and gene.gene_core != new_gene:
                logging.debug("Gene:{} in panel:{} has changed to gene:{}".format(
                    gene_symbol, self, new_gene.gene_symbol
                ))
                old_gene_symbol = gene.gene_core.gene_symbol

                evidences = gene.evidence.all()
                for evidence in evidences:
                    evidence.pk = None

                evaluations = gene.evaluation.all()
                for evaluation in evaluations:
                    evaluation.create_comments = []
                    for comment in evaluation.comments.all():
                        comment.pk = None
                        evaluation.create_comments.append(comment)
                    evaluation.pk = None

                tracks = gene.track.all()
                for track in tracks:
                    track.pk = None

                tags = gene.tags.all()

                comments = gene.comments.all()
                for comment in comments:
                    comment.pk = None

                new_gpes = gene
                new_gpes.gene_core = new_gene
                new_gpes.gene = new_gene.dict_tr()
                new_gpes.pk = None
                new_gpes.panel = self
                new_gpes.save()

                Evidence.objects.bulk_create(evidences)
                new_gpes.evidence.through.objects.bulk_create([
                    new_gpes.evidence.through(**{
                        'evidence_id': ev.pk,
                        'genepanelentrysnapshot_id': new_gpes.pk
                    }) for ev in evidences
                ])

                Evaluation.objects.bulk_create(evaluations)
                new_gpes.evaluation.through.objects.bulk_create([
                    new_gpes.evaluation.through(**{
                        'evaluation_id': ev.pk,
                        'genepanelentrysnapshot_id': new_gpes.pk
                    }) for ev in evaluations
                ])

                for evaluation in evaluations:
                    Comment.objects.bulk_create(evaluation.create_comments)

                evaluation_comments = []
                for evaluation in evaluations:
                    for comment in evaluation.create_comments:
                        evaluation_comments.append(Evaluation.comments.through(**{
                            'comment_id': comment.pk,
                            'evaluation_id': evaluation.pk
                        }))

                Evaluation.comments.through.objects.bulk_create(evaluation_comments)

                TrackRecord.objects.bulk_create(tracks)
                new_gpes.track.through.objects.bulk_create([
                    new_gpes.track.through(**{
                        'trackrecord_id': track.pk,
                        'genepanelentrysnapshot_id': new_gpes.pk
                    }) for track in tracks
                ])

                new_gpes.tags.through.objects.bulk_create([
                    new_gpes.tags.through(**{
                        'tag_id': tag.pk,
                        'genepanelentrysnapshot_id': new_gpes.pk
                    }) for tag in tags
                ])

                Comment.objects.bulk_create(comments)
                new_gpes.comments.through.objects.bulk_create([
                    new_gpes.comments.through(**{
                        'comment_id': comment.pk,
                        'genepanelentrysnapshot_id': new_gpes.pk
                    }) for comment in comments
                ])

                description = "{} was changed to {}".format(old_gene_symbol, new_gene.gene_symbol)
                track_gene = TrackRecord.objects.create(
                    gel_status=new_gpes.status,
                    curator_status=0,
                    user=user,
                    issue_type=TrackRecord.ISSUE_TYPES.ChangedGeneName,
                    issue_description=description
                )
                new_gpes.track.add(track_gene)
                self.add_activity(user, description, gene)

                if gene_symbol.startswith("MT-"):
                    new_gpes.moi = "MITOCHONDRIAL"
                    description = "Model of inheritance for gene {} was set to {}".format(
                        gene_symbol,
                        "MITOCHONDRIAL"
                    )
                    track_moi = TrackRecord.objects.create(
                        gel_status=new_gpes.status,
                        curator_status=0,
                        user=user,
                        issue_type=TrackRecord.ISSUE_TYPES.SetModeofInheritance,
                        issue_description=description
                    )
                    new_gpes.track.add(track_moi)
                    self.add_activity(user, description, gene)

                self.delete_gene(old_gene_symbol, increment=False)
                self.clear_cache()
                self.update_saved_stats()
                return gene
            elif gene_name and gene.gene.get('gene_name') != gene_name:
                logging.debug("Updating gene_name for gene:{} in panel:{}".format(gene_symbol, self))
                gene.gene['gene_name'] = gene_name
                gene.save()
            else:
                gene.save()
            self.clear_cache()
            self.update_saved_stats()
            return gene
        else:
            return False

    def add_str(self, user, str_name, str_data, increment_version=True):
        """Adds a new gene to the panel

        Args:
            user: User instance. It's the user who is adding a new gene, we need
                this info to add to TrackRecord, Activities, Evidence, and Evaluation
            str_name: STR name
            str_data: A dict with the values:
                - moi
                - penetrance
                - publications
                - phenotypes
                - comment
                - current_diagnostic
                - sources
                - rating
                - tags

        Returns:
            STR instance.
            Or False in case the gene is already in the panel.
        """

        if self.has_str(str_name):
            return False

        if increment_version:
            self = self.increment_version()

        str_item = self.cached_strs.model(
            name=str_name,
            chromosome=str_data.get('chromosome'),
            position_37=str_data.get('position_37'),
            position_38=str_data.get('position_38'),
            normal_repeats=str_data.get('normal_repeats'),
            repeated_sequence=str_data.get('repeated_sequence'),
            pathogenic_repeats=str_data.get('pathogenic_repeats'),
            panel=self,
            moi=str_data.get('moi'),
            penetrance=str_data.get('penetrance'),
            publications=str_data.get('publications'),
            phenotypes=str_data.get('phenotypes'),
            saved_gel_status=0,
            flagged=False if user.reviewer.is_GEL() else True
        )

        if str_data.get('gene'):
            gene_core = Gene.objects.get(gene_symbol=str_data['gene'].gene_symbol)
            gene_info = gene_core.dict_tr()

            str_item.gene_core = gene_core
            str_item.gene = gene_info

        str_item.save()

        self.add_activity(user, "Added STR to panel", str_item)

        for source in str_data.get('sources'):
            evidence = Evidence.objects.create(
                rating=5,
                reviewer=user.reviewer,
                name=source.strip()
            )
            str_item.evidence.add(evidence)

        evidence_status = str_item.evidence_status()
        description = "{} was added by {}".format(str_item.label, user.get_full_name())
        track_created = TrackRecord.objects.create(
            gel_status=evidence_status,
            curator_status=0,
            user=user,
            issue_type=TrackRecord.ISSUE_TYPES.Created,
            issue_description=description
        )
        str_item.track.add(track_created)
        self.add_activity(user, description, str_item)
        description = "{} was added to {} panel. Sources: {}".format(
            str_item.label,
            self.panel.name,
            ",".join(str_data.get('sources'))
        )
        track_sources = TrackRecord.objects.create(
            gel_status=evidence_status,
            curator_status=0,
            user=user,
            issue_type=TrackRecord.ISSUE_TYPES.NewSource,
            issue_description=description
        )
        str_item.track.add(track_sources)
        self.add_activity(user, description, str_item)

        tags = Tag.objects.filter(pk__in=str_data.get('tags', []))
        for tag in tags:
            logging.debug("Adding new tag:{} for {} panel:{}".format(
                tag, str_item.label, self
            ))
            str_item.tags.add(tag)

            description = "{} was added to {}. Panel: {}".format(
                tag,
                str_item.label,
                self.panel.name,
            )

            track_tags = TrackRecord.objects.create(
                gel_status=evidence_status,
                curator_status=0,
                user=user,
                issue_type=TrackRecord.ISSUE_TYPES.AddedTag,
                issue_description=description
            )
            str_item.track.add(track_tags)
            self.add_activity(user, description, str_item)

        if str_data.get('rating') or str_data.get('comment'):
            evaluation = Evaluation.objects.create(
                user=user,
                rating=str_data.get('rating'),
                mode_of_pathogenicity=str_data.get('mode_of_pathogenicity'),
                phenotypes=str_data.get('phenotypes'),
                publications=str_data.get('publications'),
                moi=str_data.get('moi'),
                current_diagnostic=str_data.get('current_diagnostic'),
                clinically_relevant=str_data.get('clinically_relevant'),
                version=self.version
            )
            comment_text = str_data.get('comment', '')
            sources = ', '.join(str_data.get('sources', []))
            if sources and comment_text:
                comment_text = comment_text + ' \nSources: ' + sources
            else:
                comment_text = 'Sources: ' + sources
            comment = Comment.objects.create(
                user=user,
                comment=comment_text
            )
            if str_data.get('comment') or str_data.get('sources', []):
                evaluation.comments.add(comment)
            str_item.evaluation.add(evaluation)
        self.clear_cache()

        str_item.evidence_status(update=True)
        self.update_saved_stats()
        return str_item

    def update_str(self, user, str_name, str_data, append_only=False, remove_gene=False):
        """Updates a STR if it exists in this panel

        Args:
            user: User instance. It's the user who is updating a gene, we need
                this info to add to TrackRecord, Activities, Evidence, and Evaluation
            str_name: STR name
            str_data: A dict with the values:
                - name
                - position_37
                - position_38
                - repeated_sequence
                - normal_range
                - prepathogenic_range
                - pathogenic_range
                - moi
                - penetrance
                - publications
                - phenotypes
                - comment
                - current_diagnostic
                - sources
                - rating
                - gene

                if `gene` is in the gene_data and it's different to the stored gene
                it will change the gene data, and remove the old gene from the panel.
            append_only: bool If it's True we don't remove evidences, but only add them
            remove_gene: bool Remove gene data from this STR

        Returns:
            STR if the gene was successfully updated, False otherwise
        """

        logging.debug("Updating STR:{} panel:{} str_data:{}".format(str_name, self, str_data))
        has_str = self.has_str(str_name)
        if has_str:
            logging.debug("Found STR:{} in panel:{}. Incrementing version.".format(str_name, self))
            str_item = self.get_str(str_name)

            if str_data.get('flagged') is not None:
                str_item.flagged = str_data.get('flagged')

            tracks = []

            if str_data.get('name') and str_data.get('name') != str_name:
                if self.has_str(str_data.get('name')):
                    logging.info("Can't change STR name as the new name already exist in panel:{}".format(self))
                    return False

                old_str_name = str_item.name

                new_evidences = str_item.evidence.all()
                for evidence in new_evidences:
                    evidence.pk = None

                new_evaluations = str_item.evaluation.all()
                for evaluation in new_evaluations:
                    evaluation.create_comments = []
                    for comment in evaluation.comments.all():
                        comment.pk = None
                        evaluation.create_comments.append(comment)
                    evaluation.pk = None

                new_tracks = str_item.track.all()
                for track in new_tracks:
                    track.pk = None

                tags = str_item.tags.all()

                new_comments = str_item.comments.all()
                for comment in new_comments:
                    comment.pk = None

                str_item.name = str_data.get('name')
                str_item.pk = None
                str_item.panel = self
                str_item.save()

                Evidence.objects.bulk_create(new_evidences)
                str_item.evidence.through.objects.bulk_create([
                    str_item.evidence.through(**{
                        'evidence_id': ev.pk,
                        'str_id': str_item.pk
                    }) for ev in new_evidences
                ])

                Evaluation.objects.bulk_create(new_evaluations)
                str_item.evaluation.through.objects.bulk_create([
                    str_item.evaluation.through(**{
                        'evaluation_id': ev.pk,
                        'str_id': str_item.pk
                    }) for ev in new_evaluations
                ])

                for evaluation in new_evaluations:
                    Comment.objects.bulk_create(evaluation.create_comments)

                evaluation_comments = []
                for evaluation in new_evaluations:
                    for comment in evaluation.create_comments:
                        evaluation_comments.append(Evaluation.comments.through(**{
                            'comment_id': comment.pk,
                            'evaluation_id': evaluation.pk
                        }))

                Evaluation.comments.through.objects.bulk_create(evaluation_comments)

                TrackRecord.objects.bulk_create(new_tracks)
                str_item.track.through.objects.bulk_create([
                    str_item.track.through(**{
                        'trackrecord_id': track.pk,
                        'str_id': str_item.pk
                    }) for track in new_tracks
                ])

                str_item.tags.through.objects.bulk_create([
                    str_item.tags.through(**{
                        'tag_id': tag.pk,
                        'str_id': str_item.pk
                    }) for tag in tags
                ])

                Comment.objects.bulk_create(new_comments)
                str_item.comments.through.objects.bulk_create([
                    str_item.comments.through(**{
                        'comment_id': comment.pk,
                        'str_id': str_item.pk
                    }) for comment in new_comments
                ])

                description = "{} was changed to {}".format(old_str_name, str_item.name)
                tracks.append((
                    TrackRecord.ISSUE_TYPES.ChangedSTRName,
                    description
                ))
                self.delete_str(old_str_name, increment=False)
                logging.debug("Changed STR name:{} to {} panel:{}".format(
                    str_name, str_data.get('name'), self
                ))

            chromosome = str_data.get('chromosome')
            if chromosome and chromosome != str_item.chromosome:
                logging.debug("Chromosome for {} was changed from {} to {} panel:{}".format(
                    str_item.label,
                    str_item.chromosome,
                    str_data.get('chromosome'),
                    self
                ))

                description = "Chromosome for {} was changed from {} to {}. Panel: {}".format(
                    str_item.name,
                    str_item.chromosome,
                    str_data.get('chromosome'),
                    self.panel.name
                )

                tracks.append((
                    TrackRecord.ISSUE_TYPES.ChangedChromosome,
                    description
                ))

                str_item.chromosome = str_data.get('chromosome')

            position_37 = str_data.get('position_37')
            if position_37 and position_37 != str_item.position_37:
                logging.debug("GRCh37 position for {} was changed from {}-{} to {}-{} panel:{}".format(
                    str_item.label,
                    str_item.position_37.lower,
                    str_item.position_37.upper,
                    str_data.get('position_37').lower,
                    str_data.get('position_37').upper,
                    self
                ))

                description = "GRCh37 position for {} was changed from {}-{} to {}-{}. Panel: {}".format(
                    str_item.name,
                    str_item.position_37.lower,
                    str_item.position_37.upper,
                    str_data.get('position_37').lower,
                    str_data.get('position_37').upper,
                    self.panel.name
                )

                tracks.append((
                    TrackRecord.ISSUE_TYPES.ChangedPosition37,
                    description
                ))

                str_item.position_37 = str_data.get('position_37')

            position_38 = str_data.get('position_38')
            if position_38 and position_38 != str_item.position_38:
                logging.debug("GRCh38 position for {} was changed from {} to {} panel:{}".format(
                    str_item.label, str_item.position_38, str_data.get('position_38'), self
                ))

                description = "GRCh38 position for {} was changed from {}-{} to {}-{}. Panel: {}".format(
                    str_item.name,
                    str_item.position_38.lower,
                    str_item.position_38.upper,
                    str_data.get('position_38').lower,
                    str_data.get('position_38').upper,
                    self.panel.name
                )

                tracks.append((
                    TrackRecord.ISSUE_TYPES.ChangedPosition38,
                    description
                ))

                str_item.position_38 = str_data.get('position_38')

            repeated_sequence = str_data.get('repeated_sequence')
            if repeated_sequence and repeated_sequence != str_item.repeated_sequence:
                logging.debug("Repeated Sequence for {} was changed from {} to {} panel:{}".format(
                    str_item.label, str_item.repeated_sequence, str_data.get('repeated_sequence'), self
                ))

                description = "Repeated Sequence for {} was changed from {} to {}. Panel: {}".format(
                    str_item.name,
                    str_item.repeated_sequence,
                    str_data.get('repeated_sequence'),
                    self.panel.name
                )

                tracks.append((
                    TrackRecord.ISSUE_TYPES.ChangedRepeatedSequence,
                    description
                ))

                str_item.repeated_sequence = str_data.get('repeated_sequence')

            normal_repeats = str_data.get('normal_repeats')
            if normal_repeats and normal_repeats != str_item.normal_repeats:
                logging.debug("Normal Number of Repeats for {} was changed from {} to {} panel:{}".format(
                    str_item.label, str_item.normal_repeats, str_data.get('normal_repeats'), self
                ))

                description = "Normal Number of Repeats for {} was changed from {} to {}. Panel: {}".format(
                    str_item.name,
                    str_item.normal_repeats,
                    str_data.get('normal_repeats'),
                    self.panel.name
                )

                tracks.append((
                    TrackRecord.ISSUE_TYPES.ChangedNormalRepeats,
                    description
                ))

                str_item.normal_repeats = str_data.get('normal_repeats')

            pathogenic_repeats = str_data.get('pathogenic_repeats')
            if pathogenic_repeats and pathogenic_repeats != str_item.pathogenic_repeats:
                logging.debug("Pathogenic Number of Repeats for {} was changed from {} to {} panel:{}".format(
                    str_item.label, str_item.pathogenic_repeats, str_data.get('pathogenic_repeats'), self
                ))

                description = "Pathogenic Number of Repeats for {} was changed from {} to {}. Panel: {}".format(
                    str_item.name,
                    str_item.pathogenic_repeats,
                    str_data.get('pathogenic_repeats'),
                    self.panel.name
                )

                tracks.append((
                    TrackRecord.ISSUE_TYPES.ChangedPathogenicRepeats,
                    description
                ))

                str_item.pathogenic_repeats = str_data.get('pathogenic_repeats')

            evidences_names = [ev.strip() for ev in str_item.evidence.values_list('name', flat=True)]

            logging.debug("Updating evidences_names for {} in panel:{}".format(str_item.label, self))
            if str_data.get('sources'):
                add_evidences = [
                    source.strip() for source in str_data.get('sources')
                    if source not in evidences_names
                ]
                delete_evidences = [
                    source for source in evidences_names
                    if source not in Evidence.EXPERT_REVIEWS and not source in str_data.get('sources')
                ]

                if not append_only:
                    for source in delete_evidences:
                        ev = str_item.evidence.filter(name=source).first()
                        str_item.evidence.remove(ev)

                for source in add_evidences:
                    logging.debug("Adding new evidence:{} for {} panel:{}".format(
                        source, str_item.label, self
                    ))
                    evidence = Evidence.objects.create(
                        name=source,
                        rating=5,
                        reviewer=user.reviewer
                    )
                    str_item.evidence.add(evidence)

                    description = "{} was added to {}. Panel: {}".format(
                        source,
                        str_item.label,
                        self.panel.name,
                    )
                    tracks.append((
                        TrackRecord.ISSUE_TYPES.NewSource,
                        description
                    ))

            moi = str_data.get('moi')
            if moi and str_item.moi != moi:
                logging.debug("Updating moi for {} in panel:{}".format(str_item.label, self))
                str_item.moi = moi

                description = "Model of inheritance for {} was set to {}".format(
                    str_item.label,
                    moi
                )
                tracks.append((
                    TrackRecord.ISSUE_TYPES.SetModeofInheritance,
                    description
                ))

            phenotypes = str_data.get('phenotypes')
            if phenotypes:
                logging.debug("Updating phenotypes for {} in panel:{}".format(str_item.label, self))
                str_item.phenotypes = phenotypes

            penetrance = str_data.get('penetrance')
            if penetrance and str_item.penetrance != penetrance:
                str_item.penetrance = penetrance
                logging.debug("Updating penetrance for {} in panel:{}".format(str_item.label, self))
                description = "Penetrance for gene {} was set to {}".format(
                    str_item.name,
                    penetrance
                )
                tracks.append((
                    TrackRecord.ISSUE_TYPES.SetPenetrance,
                    description
                ))

            publications = str_data.get('publications')
            if publications and str_item.publications != publications:
                str_item.publications = publications
                logging.debug("Updating publications for {} in panel:{}".format(str_item.label, self))
                description = "Publications for {} was set to {}".format(
                    str_item.label,
                    publications
                )
                tracks.append((
                    TrackRecord.ISSUE_TYPES.SetPublications,
                    description
                ))

            current_tags = [tag.pk for tag in str_item.tags.all()]
            tags = str_data.get('tags')
            if tags or current_tags:
                if not tags:
                    tags = []

                new_tags = [tag.pk for tag in tags]
                add_tags = [
                    tag for tag in tags
                    if tag.pk not in current_tags
                ]
                delete_tags = [
                    tag for tag in current_tags
                    if tag not in new_tags
                ]

                if not append_only:
                    for tag in delete_tags:
                        tag = str_item.tags.get(pk=tag)
                        str_item.tags.remove(tag)
                        logging.debug("Removing tag:{} for {} panel:{}".format(
                            tag.name, str_item.label, self
                        ))
                        description = "{} was removed from {}. Panel: {}".format(
                            tag,
                            str_item.label,
                            self.panel.name,
                        )
                        tracks.append((
                            TrackRecord.ISSUE_TYPES.RemovedTag,
                            description
                        ))

                for tag in add_tags:
                    logging.debug("Adding new tag:{} for {} panel:{}".format(
                        tag, str_item.label, self
                    ))
                    str_item.tags.add(tag)

                    description = "{} was added to {}. Panel: {}".format(
                        tag,
                        str_item.label,
                        self.panel.name,
                    )
                    tracks.append((
                        TrackRecord.ISSUE_TYPES.AddedTag,
                        description
                    ))

            new_gene = str_data.get('gene')
            gene_name = str_data.get('gene_name')

            if remove_gene and str_item.gene_core:
                logging.debug("{} in panel:{} was removed".format(
                    str_item.gene['gene_name'], self
                ))

                description = "Gene: {} was removed. Panel: {}".format(
                    str_item.gene_core.gene_symbol,
                    self.panel.name
                )

                tracks.append((
                    TrackRecord.ISSUE_TYPES.RemovedGene,
                    description
                ))
                str_item.gene_core = None
                str_item.gene = None

            elif new_gene and str_item.gene_core != new_gene:
                logging.debug("{} in panel:{} has changed to gene:{}".format(
                    gene_name, self, new_gene.gene_symbol
                ))

                if str_item.gene_core:
                    description = "Gene: {} was changed to {}. Panel: {}".format(
                        str_item.gene_core.gene_symbol,
                        new_gene.gene_symbol,
                        self.panel.name
                    )
                else:
                    description = "Gene was set to {}. Panel: {}".format(
                        new_gene.gene_symbol,
                        self.panel.name
                    )

                tracks.append((
                    TrackRecord.ISSUE_TYPES.AddedTag,
                    description
                ))

                str_item.gene_core = new_gene
                str_item.gene = new_gene.dict_tr()
            elif gene_name and str_item.gene.get('gene_name') != gene_name:
                logging.debug("Updating gene_name for {} in panel:{}".format(str_item.label, self))
                str_item.gene['gene_name'] = gene_name

            if tracks:
                logging.debug("Adding tracks for {} in panel:{}".format(str_item.label, self))
                status = str_item.evidence_status(True)
                description = "\n".join([t[1] for t in tracks])
                track = TrackRecord.objects.create(
                    gel_status=status,
                    curator_status=0,
                    user=user,
                    issue_type=",".join([t[0] for t in tracks]),
                    issue_description=description
                )
                str_item.track.add(track)
                self.add_activity(user, description, str_item)

            str_item.save()
            self.clear_cache()
            self.update_saved_stats()
            return str_item
        else:
            return False

    def copy_gene_reviews_from(self, genes, copy_from_panel):
        """Copy gene reviews from specified panel"""

        with transaction.atomic():
            current_genes = {gpes.gene.get('gene_symbol'): gpes for gpes in self.get_all_genes_extra.prefetch_related(
                'evidence__reviewer'
            )}
            copy_from_genes = {gpes.gene.get('gene_symbol'): gpes for gpes in copy_from_panel.get_all_genes_extra}

            # The following code goes through all evaluations and creates evaluations, evidences, comments in bulk
            new_evaluations = {}
            panel_name = copy_from_panel.level4title.name

            for gene_symbol in genes:
                if current_genes.get(gene_symbol) and copy_from_genes.get(gene_symbol):
                    copy_from_gene = copy_from_genes.get(gene_symbol)
                    gene = current_genes.get(gene_symbol)

                    filtered_evaluations = [
                        ev for ev in copy_from_gene.evaluation.all()
                        if ev.user_id not in gene.evaluators
                    ]

                    filtered_evidences = [
                        ev for ev in copy_from_gene.evidence.all()
                        if ev.reviewer and ev.reviewer.user_id not in gene.evaluators
                    ]

                    for evaluation in filtered_evaluations:
                        to_create = {
                            'gene': gene,
                            'evaluation': None,
                            'comments': [],
                            'evidences': []
                        }

                        version = evaluation.version if evaluation.version else '0'
                        evaluation.version = "Imported from {} panel version {}".format(panel_name, version)
                        to_create['evaluation'] = evaluation
                        comments = deepcopy(evaluation.comments.all())
                        evaluation.pk = None
                        evaluation.create_comments = []
                        for comment in comments:
                            comment.pk = None
                            evaluation.create_comments.append(comment)

                        new_evaluations["{}_{}".format(gene_symbol, evaluation.user_id)] = to_create

                    for evidence in filtered_evidences:
                        evidence.pk = None
                        gene_id = "{}_{}".format(gene_symbol, evidence.reviewer.user_id)
                        if new_evaluations.get(gene_id):
                            new_evaluations[gene_id]['evidences'].append(evidence)

            Evaluation.objects.bulk_create([
                new_evaluations[key]['evaluation'] for key in new_evaluations
            ])

            Evidence.objects.bulk_create([
                ev for key in new_evaluations for ev in new_evaluations[key]['evidences']
            ])

            Comment.objects.bulk_create([
                c for key in new_evaluations for c in new_evaluations[key]['evaluation'].create_comments
            ])

            evidences = []
            evaluations = []
            comments = []

            for gene_user in new_evaluations.values():
                gene_pk = gene_user['gene'].pk

                for evidence in gene_user['evidences']:
                    evidences.append({
                        'evidence_id': evidence.pk,
                        'genepanelentrysnapshot_id': gene_pk
                    })

                evaluations.append({
                    'evaluation_id': gene_user['evaluation'].pk,
                    'genepanelentrysnapshot_id': gene_pk
                })

                for comment in gene_user['evaluation'].create_comments:
                    comments.append({
                        'comment_id': comment.pk,
                        'evaluation_id': gene_user['evaluation'].pk
                    })

            self.genepanelentrysnapshot_set.model.evaluation.through.objects.bulk_create([
                self.genepanelentrysnapshot_set.model.evaluation.through(**ev) for ev in evaluations
            ])

            self.genepanelentrysnapshot_set.model.evidence.through.objects.bulk_create([
                self.genepanelentrysnapshot_set.model.evidence.through(**ev) for ev in evidences
            ])

            Evaluation.comments.through.objects.bulk_create([
                Evaluation.comments.through(**c) for c in comments
            ])

            self.update_saved_stats()
            return len(evaluations)

    def add_activity(self, user, text, entity=None):
        """Adds activity for this panel"""

        extra_info = {}
        if entity:
            extra_info = {
                'entity_name': entity.name,
                'entity_type': entity.entity_type
            }

        Activity.log(
            user=user,
            panel_snapshot=self,
            text=text,
            extra_info=extra_info
        )
