import logging
from copy import deepcopy
from django.core.cache import cache
from django.db import models
from django.db import transaction
from django.db.models import Count
from django.db.models import Case
from django.db.models import When
from django.db.models import Subquery
from django.db.models import CharField, Value as V
from django.db.models.functions import Concat
from django.db.models import Q, Value
from django.contrib.postgres.fields import JSONField
from django.urls import reverse
from django.utils import timezone
from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.aggregates import ArrayAgg
from django.utils.functional import cached_property
from model_utils.models import TimeStampedModel

from panels.tasks import email_panel_promoted
from panels.exceptions import IsSuperPanelException
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
            .distinct('panel_id')\
            .values('pk')\
            .order_by('panel_id', '-major_version', '-minor_version')

    def get_active(self, all=False, deleted=False, internal=False, name=None):
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

        qs = qs.filter(pk__in=Subquery(self.get_latest_ids(deleted)))

        if name:
            if name.isdigit():
                filters = Q(panel__pk=name)
            else:
                filters = Q(panel__old_pk=name) | Q(panel__name=name) | Q(old_panels__contains=[name])\
                          | Q(panel__name__icontains=name)
            qs = qs.filter(filters)

        return qs.prefetch_related('panel', 'level4title')\
            .order_by('panel__name', '-major_version', '-minor_version')

    def get_active_annotated(self, all=False, deleted=False, internal=False, name=None):
        """This method adds additional values to the queryset, such as number_of_genes, etc and returns active panels"""

        return self.get_active(all, deleted, internal, name)\
            .annotate(child_panels_count=Count('child_panels')) \
            .annotate(superpanels_count=Count('genepanelsnapshot')) \
            .annotate(
                is_super_panel=Case(
                    When(child_panels_count__gt=0, then=Value(True)),
                    default=Value(False),
                    output_field=models.BooleanField()
                ),
                is_child_panel=Case(
                    When(superpanels_count__gt=0, then=Value(True)),
                    default=Value(False),
                    output_field=models.BooleanField()
                ),
                unique_id=Case(
                    When(panel__old_pk__isnull=False, then=(Value('panel__old_pk'))),
                    default=Value('panel_id'),
                    output_field=models.CharField()
                )
            )

    def get_gene_panels(self, gene_symbol, all=False, internal=False):
        """Get all panels for a specific gene in Gene entities"""

        return self.get_active_annotated(all=all, internal=internal).filter(genepanelentrysnapshot__gene__gene_symbol=gene_symbol)

    def get_strs_panels(self, gene_symbol, all=False, internal=False):
        """Get all panels for a specific gene in STR entities"""

        return self.get_active_annotated(all=all, internal=internal).filter(str__gene__gene_symbol=gene_symbol)

    def get_region_panels(self, gene_symbol, all=False, internal=False):
        """Get all panels for a specific gene in Region entities"""

        return self.get_active_annotated(all=all, internal=internal).filter(str__gene__gene_symbol=gene_symbol)

    def get_shared_panels(self, gene_symbol, all=False, internal=False):
        """Get all panels for a specific gene"""

        qs = self.get_active(all=all, internal=internal)
        qs = qs.filter(genepanelentrysnapshot__gene_core__gene_symbol=gene_symbol)\
            .union(qs.filter(str__gene_core__gene_symbol=gene_symbol))\
            .union(qs.filter(region__gene_core__gene_symbol=gene_symbol))
        return qs

    def get_panels_active_panels(self, all=False, deleted=False, internal=False):
        return self.get_active(all=all, deleted=deleted, internal=internal)\
            .annotate(version=Concat('major_version', V('.'), 'minor_version', output_field=CharField()))\
            .values_list('panel_id', 'panel__name')

    def get_panel_snapshots(self, panel_id):
        return super().get_queryset().filter(panel_id=panel_id)\
            .prefetch_related('panel', 'level4title')\
            .order_by('-major_version', '-minor_version')

    def get_panel_versions(self, panel_id, all=False, deleted=False, internal=False):
        qs = self.filter(panel_id=panel_id)

        if not all:
            qs = qs.filter(Q(panel__status=GenePanel.STATUS.public) | Q(panel__status=GenePanel.STATUS.promoted))

        if not internal:
            qs = qs.exclude(panel__status=GenePanel.STATUS.internal)

        if not deleted:
            qs = qs.exclude(panel__status=GenePanel.STATUS.deleted)

        return qs.annotate(version=Concat('major_version', V('.'), 'minor_version', output_field=CharField()))\
                 .order_by('-major_version', '-minor_version')\
                 .values_list('version', 'version')

    def get_panel_entities(self, panel_id, major_version, minor_version, all=False, deleted=False, internal=False):
        qs = self.filter(panel_id=panel_id, major_version=major_version, minor_version=minor_version)

        if not all:
            qs = qs.filter(Q(panel__status=GenePanel.STATUS.public) | Q(panel__status=GenePanel.STATUS.promoted))

        if not internal:
            qs = qs.exclude(panel__status=GenePanel.STATUS.internal)

        if not deleted:
            qs = qs.exclude(panel__status=GenePanel.STATUS.deleted)

        gps = qs.first()
        if not gps:
            return []

        genes = [(g.get('gene_symbol'), g.get('gene_symbol')) for g in gps.cached_genes.values_list('gene', flat=True)]
        strs = [(n, n) for n in gps.cached_strs.values_list('name', flat=True)]

        return list(genes) + list(strs)


class GenePanelSnapshot(TimeStampedModel):
    """Main Gene Panel model

    GenePanel is just a placeholder with a static ID for a panel, all
    information for the genes is actually stored in GenePanelSnapshot.

    Every time we change something in a gene or in a panel we create a new
    spanshot and make the changes there. This allows us to preserve the changes
    between versions and we can retrieve a specific version.
    """

    SUPPORTED_ENTITIES = ['str', 'region', 'genepanelentrysnapshot']

    class Meta:
        get_latest_by = "created"
        ordering = ['-major_version', '-minor_version', ]
        indexes = [
            models.Index(fields=['panel_id', ]),
        ]

    objects = GenePanelSnapshotManager()

    level4title = models.ForeignKey(Level4Title, on_delete=models.PROTECT)
    panel = models.ForeignKey(GenePanel, on_delete=models.PROTECT)
    major_version = models.IntegerField(default=0, db_index=True)
    minor_version = models.IntegerField(default=0, db_index=True)
    version_comment = models.TextField(null=True)
    old_panels = ArrayField(models.CharField(max_length=255), blank=True, null=True)

    child_panels = models.ManyToManyField('self', symmetrical=False)
    stats = JSONField(default=dict, blank=True)

    def __str__(self):
        return "{} v{}.{}".format(self.level4title.name, self.major_version, self.minor_version)

    def get_absolute_url(self):
        return reverse('panels:detail', args=(self.panel.pk,))

    @cached_property
    def is_child_panel(self):
        return bool(self.genepanelsnapshot_set.count())

    @cached_property
    def is_super_panel(self):
        """Check if panel is super panel

        Useful as we need to check in gene evaluations, updates, rendering, imports.

        We don't store any information about entities in this panel. This panel is only for the referencing
        other panels.

        :return: bool if panel is super panel
        """
        return bool(self.child_panels.count())

    def _get_stats(self):
        """Get stats for a panel, i.e. number of reviewers, genes, evaluated genes, etc"""

        pks = [self.pk, ]
        if self.is_super_panel:
            pks = list(self.child_panels.values_list('pk', flat=True))

        keys = [
            'gene_reviewers',
            'number_of_evaluated_genes',
            'number_of_genes',
            'number_of_ready_genes',
            'number_of_green_genes',
            'str_reviewers',
            'number_of_evaluated_strs',
            'number_of_strs',
            'number_of_ready_strs',
            'number_of_green_strs',
            'region_reviewers',
            'number_of_evaluated_regions',
            'number_of_regions',
            'number_of_ready_regions',
            'number_of_green_regions',
        ]

        out = {
            'gene_reviewers': [],
            'str_reviewers': [],
            'region_reviewers': []
        }

        for pk in pks:
            # This is ~ 3000x faster than `.filter(pk__in=pks)`. Not a typo: 24 seconds vs 4ms per pk
            info = GenePanelSnapshot.objects.filter(pk=pk)\
                .prefetch_related('str',
                                  'str__evaluation',
                                  'str__evaluation__user',
                                  'genepanelentrysnapshot',
                                  'genepanelentrysnapshot__evaluation',
                                  'genepanelentrysnapshot__evaluation__user')\
                .aggregate(
                    gene_reviewers=ArrayAgg('genepanelentrysnapshot__evaluation__user__pk', distinct=True),
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
                    str_reviewers=ArrayAgg('str__evaluation__user__pk', distinct=True),
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

                    region_reviewers=ArrayAgg('region__evaluation__user__pk', distinct=True),
                    number_of_evaluated_regions=Count(Case(
                        # Count unique genes if that gene has more than 1 evaluation
                        When(
                            region__evaluation__isnull=False,
                            then=models.F('region__pk')
                        )
                    ), distinct=True),
                    number_of_regions=Count('region__pk', distinct=True),
                    number_of_ready_regions=Count(
                        Case(
                            When(
                                region__ready=True,
                                then=models.F('region__pk')
                            )
                        ),
                        distinct=True
                    ),
                    number_of_green_region=Count(
                        Case(
                            When(
                                region__saved_gel_status__gte=3,
                                then=models.F('region__pk')
                            )
                        ),
                        distinct=True
                    ),
                )

            for key in keys:
                out[key] = out.get(key, 0) + info.get(key, 0)

        out['gene_reviewers'] = list(set([r for r in out['gene_reviewers'] if r]))  #  remove None
        out['str_reviewers'] = list(set([r for r in out['str_reviewers'] if r]))  # remove None
        out['region_reviewers'] = list(set([r for r in out['str_reviewers'] if r]))  # remove None
        out['entity_reviewers'] = list(set(out['gene_reviewers'] + out['str_reviewers'] + out['region_reviewers']))
        out['number_of_reviewers'] = len(out['entity_reviewers'])
        out['number_of_evaluated_entities'] = out['number_of_evaluated_genes'] + out['number_of_evaluated_strs'] +\
                                              out['number_of_evaluated_regions']
        out['number_of_entities'] = out['number_of_genes'] + out['number_of_strs'] + out['number_of_regions']
        out['number_of_ready_entities'] = out['number_of_ready_genes'] + out['number_of_ready_strs'] +\
                                          out['number_of_ready_regions']
        out['number_of_green_entities'] = out['number_of_green_genes'] + out['number_of_green_strs'] +\
                                          out['number_of_green_regions']

        return out

    def update_saved_stats(self):
        """Get the new values from the database"""

        self.stats = self._get_stats()
        self.save(update_fields=['stats', ])

    @property
    def version(self):
        return "{}.{}".format(self.major_version, self.minor_version)

    def update_child_panels(self):
        if not self.is_super_panel:
            return

        self.increment_version()

        panels_changed = False
        updated_child_panels = []
        for child_panel in self.child_panels.all():
            active_child_panel = child_panel.panel.active_panel
            if child_panel != active_child_panel:
                panels_changed = True
                updated_child_panels.append(active_child_panel.pk)
            else:
                updated_child_panels.append(child_panel.pk)

        if panels_changed:
            self.child_panels.set(updated_child_panels)

    def increment_version(self, major=False, user=None, comment=None, ignore_gene=None, ignore_str=None, ignore_region=None):
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
            current_regions = deepcopy(self.get_all_regions)
            child_panels = list(self.child_panels.values_list('pk', flat=True))
            super_panels = list(self.genepanelsnapshot_set.values_list('pk', flat=True))

            old_pk = self.pk
            self.pk = None

            if major:
                self.major_version += 1
                self.minor_version = 0
            else:
                self.minor_version += 1

            self.save()

            if self.is_super_panel:
                # copy child panels
                self.child_panels.through.objects.bulk_create([
                    self.child_panels.through(**{
                        'to_genepanelsnapshot_id': child_panel,
                        'from_genepanelsnapshot_id': self.pk
                    }) for child_panel in child_panels
                ])
            else:
                self._increment_version_entities('genepanelentrysnapshot', current_genes, major, user, comment,
                                                 ignore_gene)
                self._increment_version_entities('str', current_strs, major, user, comment, ignore_str)
                self._increment_version_entities('region', current_regions, major, user, comment, ignore_region)

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

                # check if there are any parent panels
                if super_panels:
                    new_super_panels = []
                    for panel in GenePanelSnapshot.objects.filter(pk__in=super_panels):
                        panel.increment_version(major=major)
                        panel.child_panels.remove(old_pk)
                        new_super_panels.append(panel.pk)

                    self.child_panels.through.objects.bulk_create([
                        self.child_panels.through(**{
                            'to_genepanelsnapshot_id': self.pk,
                            'from_genepanelsnapshot_id': super_panel
                        }) for super_panel in new_super_panels
                    ])

                    for panel in self.genepanelsnapshot_set.all():
                        panel.update_saved_stats()

            return self.panel.active_panel

    def _increment_version_entities(self, entity_type, current_entities, major, user, comment, ignore_entity):
        assert entity_type in self.SUPPORTED_ENTITIES

        entity_type_id = '{entity_type}_id'.format(entity_type=entity_type)

        evidences = []
        evaluations = []
        tracks = []
        tags = []
        comments = []

        entities = {}

        for entity in current_entities:
            entity_name = entity.name if getattr(entity, 'name') else entity.gene.get('gene_symbol')

            if ignore_entity and entity_name == ignore_entity:
                continue

            old_entity = deepcopy(entity)
            entity.pk = None
            entity.panel = self

            if major:
                entity.ready = False
                entity.save()

            entities[entity_name] = {
                'entity': entity,
                'old_entity': old_entity,
                'evidences': [
                    {
                        'evidence_id': ev,
                        entity_type_id: entity.pk
                    } for ev in set(entity.evidences) if ev is not None
                ],
                'evaluations': [
                    {
                        'evaluation_id': ev,
                        entity_type_id: entity.pk
                    } for ev in set(entity.evaluations) if ev is not None
                ],
                'tracks': [
                    {
                        'trackrecord_id': ev,
                        entity_type_id: entity.pk
                    } for ev in set(entity.tracks) if ev is not None
                ],
                'tags': [
                    {
                        'tag_id': ev,
                        entity_type_id: entity.pk
                    } for ev in set(entity.gene_tags) if ev is not None
                ],
                'comments': [
                    {
                        'comment_id': ev,
                        entity_type_id: entity.pk
                    } for ev in set(entity.comment_pks) if ev is not None
                ]
            }

            if major and user and comment:
                issue_type = "Panel promoted to version {}".format(self.version)
                issue_description = comment

                track_promoted = TrackRecord.objects.create(
                    curator_status=user.reviewer.is_GEL(),
                    issue_description=issue_description,
                    gel_status=entity.status,
                    issue_type=issue_type,
                    user=user
                )
                entity.track.add(track_promoted)

        entity_set = getattr(self, '{entity_type}_set'.format(entity_type=entity_type))

        # add in bulk
        if not major:
            bulk_entities = [entities[entity_key]['entity'] for entity_key in entities]
            new_entities = entity_set.model.objects.bulk_create(bulk_entities)
        else:
            new_entities = entity_set.all()

        self.clear_cache()

        for entity in new_entities:
            entity_name = entity.name if getattr(entity, 'name') else entity.gene.get('gene_symbol')
            entity_data = entities[entity_name]

            for i, _ in enumerate(entity_data['evidences']):
                entity_data['evidences'][i][entity_type_id] = entity_data['entity'].pk
            evidences.extend(entity_data['evidences'])

            for i, _ in enumerate(entity_data['evaluations']):
                entity_data['evaluations'][i][entity_type_id] = entity_data['entity'].pk
            evaluations.extend(entity_data['evaluations'])

            for i, _ in enumerate(entity_data['tracks']):
                entity_data['tracks'][i][entity_type_id] = entity_data['entity'].pk
            tracks.extend(entity_data['tracks'])

            for i, _ in enumerate(entity_data['tags']):
                entity_data['tags'][i][entity_type_id] = entity_data['entity'].pk
            tags.extend(entity_data['tags'])

            for i, _ in enumerate(entity_data['comments']):
                entity_data['comments'][i][entity_type_id] = entity_data['entity'].pk
            comments.extend(entity_data['comments'])

        entity_set.model.evidence.through.objects.bulk_create([
            entity_set.model.evidence.through(**ev) for ev in evidences
        ])
        entity_set.model.evaluation.through.objects.bulk_create([
            entity_set.model.evaluation.through(**ev) for ev in evaluations
        ])
        entity_set.model.track.through.objects.bulk_create([
            entity_set.model.track.through(**ev) for ev in tracks
        ])
        entity_set.model.tags.through.objects.bulk_create([
            entity_set.model.tags.through(**ev) for ev in tags
        ])
        entity_set.model.comments.through.objects.bulk_create([
            entity_set.model.comments.through(**ev) for ev in comments
        ])
        self.clear_cache()

    def update_saved_stats(self):
        """Get the new values from the database"""

        out = self._get_stats()
        out['number_of_reviewers'] = len(out['entity_reviewers'])
        out['number_of_evaluated_entities'] = out['number_of_evaluated_genes'] + out['number_of_evaluated_strs']
        out['number_of_entities'] = out['number_of_genes'] + out['number_of_strs']
        out['number_of_ready_entities'] = out['number_of_ready_genes'] + out['number_of_ready_strs']
        out['number_of_green_entities'] = out['number_of_green_genes'] + out['number_of_green_strs']
        self.stats = out
        self.save(update_fields=['stats', ])

    @property
    def contributors(self):
        """Returns a tuple with user data

        Returns:
            A tuple with the user first and last name, email, and reviewer affiliation
        """

        genes_contributors = list(self.cached_genes
                                      .distinct('evaluation__user')
                                      .values_list(
                                        'evaluation__user__first_name',
                                        'evaluation__user__last_name',
                                        'evaluation__user__email',
                                        'evaluation__user__reviewer__affiliation',
                                        'evaluation__user__username'
                                      ).order_by('evaluation__user'))

        strs_contributors = list(self.cached_strs
                                     .distinct('evaluation__user')
                                     .values_list(
                                        'evaluation__user__first_name',
                                        'evaluation__user__last_name',
                                        'evaluation__user__email',
                                        'evaluation__user__reviewer__affiliation',
                                        'evaluation__user__username'
                                     ).order_by('evaluation__user'))

        region_contributors = list(self.cached_regions
                                       .distinct('evaluation__user')
                                       .values_list(
                                           'evaluation__user__first_name',
                                           'evaluation__user__last_name',
                                           'evaluation__user__email',
                                           'evaluation__user__reviewer__affiliation',
                                           'evaluation__user__username'
                                       ).order_by('evaluation__user'))

        return list(set(strs_contributors + genes_contributors + region_contributors))

    def mark_entities_not_ready(self):
        """Mark entities (genes, STRs, regions) as not ready

        Returns:
             None
        """

        if self.is_super_panel:
            raise IsSuperPanelException

        self.cached_genes.update(ready=False)
        self.cached_strs.update(ready=False)
        self.cached_regions.update(ready=False)

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
        if self.is_super_panel:
            child_panels = self.child_panels.values_list('pk', flat=True)
            qs = self.genepanelentrysnapshot_set.model.objects.filter(panel__pk__in=child_panels)\
                .all()\
                .prefetch_related('panel', 'panel__level4title', 'panel__panel', 'evidence',
                                  'evaluation', 'tags', 'evaluation__user__reviewer')
        else:
            qs = self.genepanelentrysnapshot_set.all()

        return qs.annotate(
            entity_type=V('gene', output_field=models.CharField()),
            entity_name=models.F('gene_core__gene_symbol')
        ).order_by('entity_name')

    @cached_property
    def cached_strs(self):
        if self.is_super_panel:
            child_panels = self.child_panels.values_list('pk', flat=True)
            qs = self.str_set.model.objects.filter(panel__pk__in=child_panels) \
                .all() \
                .prefetch_related('panel', 'panel__level4title', 'panel__panel', 'evidence',
                                  'evaluation', 'tags', 'evaluation__user__reviewer')
        else:
            qs = self.str_set.all()

        return qs.annotate(
            entity_type=V('str', output_field=models.CharField()),
            entity_name=models.F('name')
        ).order_by('entity_name')

    @cached_property
    def cached_regions(self):
        if self.is_super_panel:
            child_panels = self.child_panels.values_list('pk', flat=True)
            qs = self.region_set.model.objects.filter(panel__pk__in=child_panels) \
                .all() \
                .prefetch_related('panel', 'panel__level4title', 'panel__panel', 'evidence',
                                  'evaluation', 'tags', 'evaluation__user__reviewer')
        else:
            qs = self.region_set.all()

        return qs.annotate(
            entity_type=V('str', output_field=models.CharField()),
            entity_name=models.F('name')
        ).order_by('entity_name')

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

    @staticmethod
    def get_all(qs):
        return qs.annotate(
                evidences=ArrayAgg('evidence__pk', distinct=True),
                evaluations=ArrayAgg('evaluation__pk', distinct=True),
                gene_tags=ArrayAgg('tags__pk', distinct=True),
                tracks=ArrayAgg('track__pk', distinct=True),
                comment_pks=ArrayAgg('comments__pk', distinct=True)
            )

    @cached_property
    def get_all_genes(self):
        """Returns all Genes for this panel"""

        return self.get_all(self.cached_genes)

    @cached_property
    def get_all_strs(self):
        """Returns all Genes for this panel"""

        return self.get_all(self.cached_strs)

    @property
    def all_evaluations(self):
        gene_evaluations = self.get_all_genes.aggregate(evaluations=ArrayAgg('evaluations', distinct=True))
        str_evaluations = self.get_all_strs.aggregate(evaluations=ArrayAgg('evaluations', distinct=True))




    @cached_property
    def get_all_entities_extra(self):
        """Get all genes and annotated info, speeds up loading time"""
        res = list(self.get_all_genes_extra) + list(self.get_all_strs_extra) + list(self.get_all_regions_extra)
        return sorted(res, key=lambda x: (x.saved_gel_status * -1, x.entity_name.lower()))

    @cached_property
    def get_all_regions(self):
        """Returns all Regions for this panel"""
        return self.get_all(self.cached_regions)

    @staticmethod
    def get_all_extra(qs):
        return qs.prefetch_related(
                'evidence',
                'evidence__reviewer',
                'evaluation',
                'evaluation__user',
                'evaluation__user__reviewer',
                'tags'
            )\
            .annotate(
                entity_type=V('gene', output_field=models.CharField()),
                entity_name=models.F('gene_core__gene_symbol'),
                number_of_green_evaluations=Count(Case(When(
                    evaluation__rating="GREEN", then=models.F('evaluation__pk'))
                ), distinct=True),
                number_of_red_evaluations=Count(Case(When(
                    evaluation__rating="RED", then=models.F('evaluation__pk'))
                ), distinct=True),
                evaluators=ArrayAgg('evaluation__user__pk'),
                number_of_evaluations=Count('evaluation__pk', distinct=True)
            )\
            .order_by('-saved_gel_status', 'entity_name')

    @cached_property
    def get_all_genes_extra(self):
        """Get all genes and annotated info, speeds up loading time"""

        return self.get_all_extra(self.cached_genes.annotate(
            entity_type=V('gene', output_field=models.CharField()),
            entity_name=models.F('gene_core__gene_symbol')
        ))

    @cached_property
    def get_all_strs_extra(self):
        """Get all strs and annotated info, speeds up loading time"""

        return self.get_all_extra(self.cached_strs.annotate(
            entity_type=V('str', output_field=models.CharField()),
            entity_name=models.F('name')
        ))

    @cached_property
    def get_all_regions_extra(self):
        """Get all genes and annotated info, speeds up loading time"""

        return self.get_all_extra(self.cached_regions.annotate(
            entity_type=V('region', output_field=models.CharField()),
            entity_name=models.F('name')
        ))

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

    def get_entity(self, entity_name, method_type, use_gene, prefetch_extra):
        assert method_type in ['genes', 'strs', 'regions']

        if prefetch_extra:
            qs = getattr(self, 'get_all_{}_extra'.format(method_type)).prefetch_related(
                'evaluation__comments',
                'evaluation__user__reviewer',
                'track',
                'track__user',
                'track__user__reviewer'
            )
        else:
            qs = getattr(self, 'get_all_{}'.format(method_type))

        if use_gene:
            return qs.get(gene__gene_symbol=entity_name)
        else:
            return qs.get(name=entity_name)

    def get_gene(self, gene_symbol, prefetch_extra=False):
        """Get a gene for a specific gene symbol."""

        return self.get_entity(gene_symbol, 'genes', True, prefetch_extra)

    def has_gene(self, gene_symbol):
        """Check if the panel has a gene with the provided gene symbol"""

        if self.is_super_panel:
            raise IsSuperPanelException

        return gene_symbol in [
            symbol.get('gene_symbol') for symbol in self.cached_genes.values_list('gene', flat=True)
        ]

    def get_str(self, name, prefetch_extra=False):
        """Get a STR."""

        if self.is_super_panel:
            raise IsSuperPanelException

        return self.get_entity(name, 'strs', False, prefetch_extra)

    def has_str(self, str_name):
        if self.is_super_panel:
            raise IsSuperPanelException

        return self.str_set.filter(name=str_name).count() > 0

    def get_region(self, name, prefetch_extra=False):
        """Get a Region."""

        return self.get_entity(name, 'regions', False, prefetch_extra)

    def has_region(self, region_name):
        return self.region_set.filter(name=region_name).count() > 0

    def clear_cache(self):
        to_clear = [
            'cached_genes',
            'current_genes_count',
            'current_genes_duplicates',
            'current_genes',
            'get_all_genes',
            'get_all_genes_extra',
            'cached_strs',
            'get_all_strs',
            'get_all_strs_extra',
            'cached_regions',
            'get_all_regions',
            'get_all_regions_extra'
        ]

        for item in to_clear:
            if self.__dict__.get(item):
                del self.__dict__[item]

    @staticmethod
    def clear_django_cache():
        cache.delete('entities')
        cache.delete('entities_admin')

    def delete_gene(self, gene_symbol, increment=True, user=None):
        """Removes gene from a panel, but leaves it in the previous versions of the same panel"""

        if self.is_super_panel:
            raise IsSuperPanelException

        if self.has_gene(gene_symbol):
            if increment:
                self = self.increment_version(ignore_gene=gene_symbol)
            else:
                self.get_all_genes.get(gene__gene_symbol=gene_symbol).delete()
                self.clear_cache()
                self.clear_django_cache()

            if user:
                self.add_activity(user, "removed gene:{} from the panel".format(gene_symbol))

            self.update_saved_stats()
            return True
        else:
            return False

    def delete_str(self, str_name, increment=True, user=None):
        """Removes STR from a panel, but leaves it in the previous versions of the same panel"""

        if self.is_super_panel:
            raise IsSuperPanelException

        if self.has_str(str_name):
            if increment:
                self = self.increment_version(ignore_str=str_name)
            else:
                self.cached_strs.get(name=str_name).delete()
                self.clear_cache()
                self.clear_django_cache()

            if user:
                self.add_activity(user, "removed STR:{} from the panel".format(str_name))

            self.update_saved_stats()
            return True
        else:
            return False

    def delete_region(self, region_name, increment=True):
        """Removes Region from a panel, but leaves it in the previous versions of the same panel"""

        if self.has_region(region_name):
            if increment:
                self = self.increment_version(ignore_region=region_name)
            else:
                self.cached_regions.get(name=region_name).delete()
                self.clear_cache()
                self.clear_django_cache()

            self.update_saved_stats()
            return True
        else:
            return False

    def add_entity_info(self, entity, user, entity_name, entity_data):
        """Add entity common info to the database

        :param entity: Entity object
        :param user: User - Request user
        :param entity_name: str - Entity name
        :param entity_data: Dict entity data (form)
        :return:
        """

        if entity_data.get('comment'):
            comment = Comment.objects.create(
                user=user,
                comment=entity_data.get('comment')
            )
            entity.comments.add(comment)

        for source in entity_data.get('sources'):
            evidence = Evidence.objects.create(
                rating=5,
                reviewer=user.reviewer,
                name=source.strip()
            )
            entity.evidence.add(evidence)

        evidence_status = entity.evidence_status()
        tracks = []

        tracks.append((
            TrackRecord.ISSUE_TYPES.Created,
            "{} was added by {}".format(entity_name, user.get_full_name())
        ))

        description = "{} was added to {}. Sources: {}".format(
            entity_name,
            self.panel.name,
            ",".join(entity_data.get('sources'))
        )
        tracks.append((
            TrackRecord.ISSUE_TYPES.NewSource,
            description
        ))

        tags = Tag.objects.filter(pk__in=entity_data.get('tags', []))
        entity.tags.add(*entity_data.get('tags', []))

        description = "{} tags were added to {}.".format(
            ', '.join([str(tag) for tag in tags]),
            entity_name
        )
        tracks.append((
            TrackRecord.ISSUE_TYPES.AddedTag,
            description
        ))

        if entity.gene and entity.gene.get('gene_symbol', '').startswith("MT-"):
            entity.moi = "MITOCHONDRIAL"
            description = "Mode of inheritance for gene {} was set to {}".format(
                entity_name,
                "MITOCHONDRIAL"
            )
            tracks.append((
                TrackRecord.ISSUE_TYPES.SetModeofInheritance,
                description
            ))

        comment_text = entity_data.get('comment', '')
        if entity_data.get('rating') or entity_data.get('comment') or entity_data.get('source'):
            evaluation = Evaluation.objects.create(
                user=user,
                rating=entity_data.get('rating'),
                mode_of_pathogenicity=entity_data.get('mode_of_pathogenicity'),
                phenotypes=entity_data.get('phenotypes'),
                publications=entity_data.get('publications'),
                moi=entity_data.get('moi'),
                current_diagnostic=entity_data.get('current_diagnostic'),
                clinically_relevant=entity_data.get('clinically_relevant'),
                version=self.version
            )
            comment_text = entity_data.get('comment', '')
            sources = ', '.join(entity_data.get('sources', []))
            if sources and comment_text:
                comment_text = comment_text + ' \nSources: ' + sources
            else:
                comment_text = 'Sources: ' + sources
            comment = Comment.objects.create(
                user=user,
                comment=comment_text
            )
            if entity_data.get('comment') or entity_data.get('sources', []):
                evaluation.comments.add(comment)
            entity.evaluation.add(evaluation)

        if tracks:
            description = "\n".join([t[1] for t in tracks])
            track = TrackRecord.objects.create(
                gel_status=evidence_status,
                curator_status=0,
                user=user,
                issue_type=",".join([t[0] for t in tracks]),
                issue_description=description
            )
            entity.track.add(track)

            if comment_text:
                description = description + '\nAdded comment: ' + comment_text
            self.add_activity(user, description, entity)

        self.clear_cache()
        self.clear_django_cache()
        return entity

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

        if self.is_super_panel:
            raise IsSuperPanelException

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
            type_of_variants=gene_data.get('type_of_variants', self.cached_regions.model.VARIANT_TYPES.small),
            saved_gel_status=0,
            flagged=False if user.reviewer.is_GEL() else True
        )
        gene.save()

        gene = self.add_entity_info(gene, user, gene.label, gene_data)

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
        if self.is_super_panel:
            raise IsSuperPanelException


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

                description = "Mode of inheritance for gene {} was set to {}".format(
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
                description = "Mode of inheritance for gene {} was set to {}".format(
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

                description = "Mode of pathogenicity for gene {} was set to {}".format(
                    gene_symbol,
                    mop
                )
                tracks.append((
                    TrackRecord.ISSUE_TYPES.SetModeofPathogenicity,
                    description
                ))

            type_of_variants = gene_data.get('type_of_variants')
            if type_of_variants and type_of_variants != gene.type_of_variants:
                logging.debug("Variant Type for {} was changed from {} to {} panel:{}".format(
                    gene.label, gene.type_of_variants, gene_data.get('type_of_variants'), self
                ))

                description = "Variant type for {} was changed from {} to {}. Panel: {}".format(
                    gene.name,
                    gene.type_of_variants,
                    gene_data.get('type_of_variants'),
                    self.panel.name
                )

                tracks.append((
                    TrackRecord.ISSUE_TYPES.ChangedVariantType,
                    description
                ))

                gene.type_of_variants = gene_data.get('type_of_variants')

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
                    description = "Mode of inheritance for gene {} was set to {}".format(
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
                self.clear_django_cache()
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
                - chromosome
                - position_37
                - position_38
                - normal_repeats
                - pathogenic_repeats
                - repeated_sequence
                - moi
                - penetrance
                - publications
                - phenotypes
                - comment
                - current_diagnostic
                - sources
                - rating
                - tags
            increment_version: (optional) Boolean

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
        str_item = self.add_entity_info(str_item, user, str_item.label, str_data)

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
        if self.is_super_panel:
            raise IsSuperPanelException


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

                description = "Mode of inheritance for {} was set to {}".format(
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
                self.clear_django_cache()
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
                self.clear_django_cache()
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

    def add_region(self, user, region_name, region_data, increment_version=True):
        """Adds a new gene to the panel

        Args:
            user: User instance. It's the user who is adding a new gene, we need
                this info to add to TrackRecord, Activities, Evidence, and Evaluation
            str_name: STR name
            str_data: A dict with the values:
                - chromosome
                - position_37
                - position_38
                - type_of_variants
                - type_of_effects[]
                - moi
                - penetrance
                - publications
                - phenotypes
                - comment
                - current_diagnostic
                - sources
                - rating
                - tags
            increment_version: (optional) Boolean

        Returns:
            STR instance.
            Or False in case the gene is already in the panel.
        """

        if self.has_region(region_name):
            return False

        if increment_version:
            self = self.increment_version()

        region = self.cached_regions.model(
            name=region_name,
            verbose_name=region_data.get('verbose_name'),
            chromosome=region_data.get('chromosome'),
            position_37=region_data.get('position_37'),
            position_38=region_data.get('position_38'),
            haploinsufficiency_score=region_data.get('haploinsufficiency_score'),
            triplosensitivity_score=region_data.get('triplosensitivity_score'),
            required_overlap_percentage=region_data.get('required_overlap_percentage'),
            type_of_variants=region_data.get('type_of_variants', self.cached_regions.model.VARIANT_TYPES.small),
            panel=self,
            moi=region_data.get('moi'),
            penetrance=region_data.get('penetrance'),
            publications=region_data.get('publications'),
            phenotypes=region_data.get('phenotypes'),
            saved_gel_status=0,
            flagged=False if user.reviewer.is_GEL() else True
        )

        if region_data.get('gene'):
            gene_core = Gene.objects.get(gene_symbol=region_data['gene'].gene_symbol)
            gene_info = gene_core.dict_tr()

            region.gene_core = gene_core
            region.gene = gene_info

        region.save()
        region = self.add_entity_info(region, user, region.label, region_data)

        region.evidence_status(update=True)
        self.update_saved_stats()
        return region

    def update_region(self, user, region_name, region_data, append_only=False, remove_gene=False):
        """Updates a Region if it exists in this panel

        Args:
            user: User instance. It's the user who is updating a gene, we need
                this info to add to TrackRecord, Activities, Evidence, and Evaluation
            region_name: Region name
            region_data: A dict with the values:
                - name
                - chromosome
                - position_37
                - position_38
                - type_of_variants
                - type_of_effects
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
            remove_gene: bool Remove gene data from this region

        Returns:
            Region if the it was successfully updated, False otherwise
        """

        logging.debug("Updating Region:{} panel:{} region_data:{}".format(region_name, self, region_data))
        has_region = self.has_region(region_name)
        if has_region:
            logging.debug("Found Region:{} in panel:{}. Incrementing version.".format(region_name, self))
            region = self.get_region(region_name)

            if region_data.get('flagged') is not None:
                region.flagged = region_data.get('flagged')

            tracks = []

            if region_data.get('name') and region_data.get('name') != region_name:
                if self.has_region(region_data.get('name')):
                    logging.info("Can't change Region name as the new name already exist in panel:{}".format(self))
                    return False

                old_region_name = region.name

                new_evidences = region.evidence.all()
                for evidence in new_evidences:
                    evidence.pk = None

                new_evaluations = region.evaluation.all()
                for evaluation in new_evaluations:
                    evaluation.create_comments = []
                    for comment in evaluation.comments.all():
                        comment.pk = None
                        evaluation.create_comments.append(comment)
                    evaluation.pk = None

                new_tracks = region.track.all()
                for track in new_tracks:
                    track.pk = None

                tags = region.tags.all()

                new_comments = region.comments.all()
                for comment in new_comments:
                    comment.pk = None

                region.name = region_data.get('name')
                region.pk = None
                region.panel = self
                region.save()

                Evidence.objects.bulk_create(new_evidences)
                region.evidence.through.objects.bulk_create([
                    region.evidence.through(**{
                        'evidence_id': ev.pk,
                        'region_id': region.pk
                    }) for ev in new_evidences
                ])

                Evaluation.objects.bulk_create(new_evaluations)
                region.evaluation.through.objects.bulk_create([
                    region.evaluation.through(**{
                        'evaluation_id': ev.pk,
                        'region_id': region.pk
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
                region.track.through.objects.bulk_create([
                    region.track.through(**{
                        'trackrecord_id': track.pk,
                        'region_id': region.pk
                    }) for track in new_tracks
                ])

                region.tags.through.objects.bulk_create([
                    region.tags.through(**{
                        'tag_id': tag.pk,
                        'region_id': region.pk
                    }) for tag in tags
                ])

                Comment.objects.bulk_create(new_comments)
                region.comments.through.objects.bulk_create([
                    region.comments.through(**{
                        'comment_id': comment.pk,
                        'region_id': region.pk
                    }) for comment in new_comments
                ])

                description = "{} was changed to {}".format(old_region_name, region.name)
                track_gene = TrackRecord.objects.create(
                    gel_status=region.status,
                    curator_status=0,
                    user=user,
                    issue_type=TrackRecord.ISSUE_TYPES.ChangedName,
                    issue_description=description
                )
                region.track.add(track_gene)
                self.delete_region(old_region_name, increment=False)
                logging.debug("Changed region name:{} to {} panel:{}".format(
                    region_name, region_data.get('name'), self
                ))

            chromosome = region_data.get('chromosome')
            if chromosome and chromosome != region.chromosome:
                logging.debug("Chromosome for {} was changed from {} to {} panel:{}".format(
                    region.label,
                    region.chromosome,
                    region_data.get('chromosome'),
                    self
                ))

                description = "Chromosome for {} was changed from {} to {}. Panel: {}".format(
                    region.name,
                    region.chromosome,
                    region_data.get('chromosome'),
                    self.panel.name
                )

                tracks.append((
                    TrackRecord.ISSUE_TYPES.ChangedChromosome,
                    description
                ))

                region.chromosome = region_data.get('chromosome')

            position_37 = region_data.get('position_37')
            if position_37 and position_37 != region.position_37:
                logging.debug("GRCh37 position for {} was changed from {}-{} to {}-{} panel:{}".format(
                    region.label,
                    region.position_37.lower,
                    region.position_37.upper,
                    region_data.get('position_37').lower,
                    region_data.get('position_37').upper,
                    self
                ))

                description = "GRCh37 position for {} was changed from {}-{} to {}-{}. Panel: {}".format(
                    region.name,
                    region.position_37.lower,
                    region.position_37.upper,
                    region_data.get('position_37').lower,
                    region_data.get('position_37').upper,
                    self.panel.name
                )

                tracks.append((
                    TrackRecord.ISSUE_TYPES.ChangedPosition37,
                    description
                ))

                region.position_37 = region_data.get('position_37')

            position_38 = region_data.get('position_38')
            if position_38 and position_38 != region.position_38:
                logging.debug("GRCh38 position for {} was changed from {} to {} panel:{}".format(
                    region.label, region.position_38, region_data.get('position_38'), self
                ))

                description = "GRCh38 position for {} was changed from {}-{} to {}-{}. Panel: {}".format(
                    region.name,
                    region.position_38.lower,
                    region.position_38.upper,
                    region_data.get('position_38').lower,
                    region_data.get('position_38').upper,
                    self.panel.name
                )

                tracks.append((
                    TrackRecord.ISSUE_TYPES.ChangedPosition38,
                    description
                ))

                region.position_38 = region_data.get('position_38')

            type_of_variants = region_data.get('type_of_variants')
            if type_of_variants and type_of_variants != region.type_of_variants:
                logging.debug("Variant Type for {} was changed from {} to {} panel:{}".format(
                    region.label, region.type_of_variants, region_data.get('type_of_variants'), self
                ))

                description = "Variant type for {} was changed from {} to {}. Panel: {}".format(
                    region.name,
                    region.type_of_variants,
                    region_data.get('type_of_variants'),
                    self.panel.name
                )

                tracks.append((
                    TrackRecord.ISSUE_TYPES.ChangedVariantType,
                    description
                ))

                region.type_of_variants = region_data.get('type_of_variants')

            type_of_effects = sorted(region_data.get('type_of_effects', []))
            if type_of_effects and type_of_effects != sorted(region.type_of_effects):
                logging.debug("Variant effects for {} were changed from {} to {} panel:{}".format(
                    region.label, region.type_of_effects, region_data.get('type_of_effects'), self
                ))

                description = "Type of effects for {} was changed from {} to {}. Panel: {}".format(
                    region.name,
                    '; '.join(region.type_of_effects),
                    '; '.join(region_data.get('type_of_effects', [])),
                    self.panel.name
                )

                tracks.append((
                    TrackRecord.ISSUE_TYPES.ChangedEffectTypes,
                    description
                ))

                region.normal_repeats = region_data.get('type_of_effects')


            evidences_names = [ev.strip() for ev in region.evidence.values_list('name', flat=True)]

            logging.debug("Updating evidences_names for {} in panel:{}".format(region.label, self))
            if region_data.get('sources'):
                add_evidences = [
                    source.strip() for source in region_data.get('sources')
                    if source not in evidences_names
                ]
                delete_evidences = [
                    source for source in evidences_names
                    if source not in Evidence.EXPERT_REVIEWS and not source in region_data.get('sources')
                ]

                if not append_only:
                    for source in delete_evidences:
                        ev = region.evidence.filter(name=source).first()
                        region.evidence.remove(ev)

                for source in add_evidences:
                    logging.debug("Adding new evidence:{} for {} panel:{}".format(
                        source, region.label, self
                    ))
                    evidence = Evidence.objects.create(
                        name=source,
                        rating=5,
                        reviewer=user.reviewer
                    )
                    region.evidence.add(evidence)

                    description = "{} was added to {}. Panel: {}".format(
                        source,
                        region.label,
                        self.panel.name,
                    )
                    tracks.append((
                        TrackRecord.ISSUE_TYPES.NewSource,
                        description
                    ))

            moi = region_data.get('moi')
            if moi and region.moi != moi:
                logging.debug("Updating moi for {} in panel:{}".format(region.label, self))
                region.moi = moi

                description = "Model of inheritance for {} was set to {}".format(
                    region.label,
                    moi
                )
                tracks.append((
                    TrackRecord.ISSUE_TYPES.SetModeofInheritance,
                    description
                ))

            phenotypes = region_data.get('phenotypes')
            if phenotypes:
                logging.debug("Updating phenotypes for {} in panel:{}".format(region.label, self))
                region.phenotypes = phenotypes

            penetrance = region_data.get('penetrance')
            if penetrance and region.penetrance != penetrance:
                region.penetrance = penetrance
                logging.debug("Updating penetrance for {} in panel:{}".format(region.label, self))
                description = "Penetrance for gene {} was set to {}".format(
                    region.name,
                    penetrance
                )
                tracks.append((
                    TrackRecord.ISSUE_TYPES.SetPenetrance,
                    description
                ))

            publications = region_data.get('publications')
            if publications and region.publications != publications:
                region.publications = publications
                logging.debug("Updating publications for {} in panel:{}".format(region.label, self))
                description = "Publications for {} was set to {}".format(
                    region.label,
                    publications
                )
                tracks.append((
                    TrackRecord.ISSUE_TYPES.SetPublications,
                    description
                ))

            current_tags = [tag.pk for tag in region.tags.all()]
            tags = region_data.get('tags')
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
                        tag = region.tags.get(pk=tag)
                        region.tags.remove(tag)
                        logging.debug("Removing tag:{} for {} panel:{}".format(
                            tag.name, region.label, self
                        ))
                        description = "{} was removed from {}. Panel: {}".format(
                            tag,
                            region.label,
                            self.panel.name,
                        )
                        tracks.append((
                            TrackRecord.ISSUE_TYPES.RemovedTag,
                            description
                        ))

                for tag in add_tags:
                    logging.debug("Adding new tag:{} for {} panel:{}".format(
                        tag, region.label, self
                    ))
                    region.tags.add(tag)

                    description = "{} was added to {}. Panel: {}".format(
                        tag,
                        region.label,
                        self.panel.name,
                    )
                    tracks.append((
                        TrackRecord.ISSUE_TYPES.AddedTag,
                        description
                    ))

            new_gene = region_data.get('gene')
            gene_name = region_data.get('gene_name')

            if remove_gene and region.gene_core:
                logging.debug("{} in panel:{} was removed".format(
                    region.gene['gene_name'], self
                ))

                description = "Gene: {} was removed. Panel: {}".format(
                    region.gene_core.gene_symbol,
                    self.panel.name
                )

                tracks.append((
                    TrackRecord.ISSUE_TYPES.RemovedGene,
                    description
                ))
                region.gene_core = None
                region.gene = None
                self.clear_django_cache()
            elif new_gene and region.gene_core != new_gene:
                logging.debug("{} in panel:{} has changed to gene:{}".format(
                    gene_name, self, new_gene.gene_symbol
                ))

                if region.gene_core:
                    description = "Gene: {} was changed to {}. Panel: {}".format(
                        region.gene_core.gene_symbol,
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

                region.gene_core = new_gene
                region.gene = new_gene.dict_tr()
                self.clear_django_cache()
            elif gene_name and region.gene.get('gene_name') != gene_name:
                logging.debug("Updating gene_name for {} in panel:{}".format(region.label, self))
                region.gene['gene_name'] = gene_name

            if tracks:
                logging.debug("Adding tracks for {} in panel:{}".format(region.label, self))
                status = region.evidence_status(True)
                track = TrackRecord.objects.create(
                    gel_status=status,
                    curator_status=0,
                    user=user,
                    issue_type=",".join([t[0] for t in tracks]),
                    issue_description="\n".join([t[1] for t in tracks])
                )
                region.track.add(track)

            region.save()
            self.clear_cache()
            self.update_saved_stats()
            return region
        else:
            return False

    def copy_gene_reviews_from(self, genes, copy_from_panel):
        """Copy gene reviews from specified panel"""
        if self.is_super_panel:
            raise IsSuperPanelException

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
                'entity_type': entity._entity_type
            }

        Activity.log(
            user=user,
            panel_snapshot=self,
            text=text,
            extra_info=extra_info
        )
