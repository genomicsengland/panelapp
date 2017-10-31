import logging
from copy import deepcopy
from django.db import models
from django.db import transaction
from django.db.models import Count
from django.db.models import Case
from django.db.models import When
from django.db.models import Subquery
from django.urls import reverse
from django.utils import timezone
from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.aggregates import ArrayAgg
from django.utils.functional import cached_property
from model_utils.models import TimeStampedModel

from panels.tasks import email_panel_promoted
from panels.utils import remove_non_ascii
from .activity import Activity
from .genepanel import GenePanel
from .Level4Title import Level4Title
from .trackrecord import TrackRecord
from .evidence import Evidence
from .evaluation import Evaluation
from .gene import Gene
from .comment import Comment
from backups.models import PanelBackup


class GenePanelSnapshotManager(models.Manager):
    def get_latest_ids(self, deleted=False):
        "Get latest versions for GenePanelsSnapshots"

        qs = super().get_queryset()
        if not deleted:
            qs = qs.exclude(panel__deleted=True)

        return qs\
            .distinct('panel__pk')\
            .values('pk')\
            .order_by('panel__pk', '-major_version', '-minor_version')

    def get_active(self, all=False, deleted=False):
        "Get all active panels"

        qs = super().get_queryset()

        if not all:
            qs = qs.filter(panel__approved=True)

        return qs.filter(pk__in=Subquery(self.get_latest_ids(deleted)))\
            .prefetch_related('panel', 'level4title')\
            .order_by('panel__name', '-major_version', '-minor_version')

    def get_active_anotated(self, all=False, deleted=False):
        "This method adds additional values to the queryset, such as number_of_genes, etc and returns active panels"

        return self.get_active(all, deleted)

    def get_gene_panels(self, gene_symbol):
        "Get all panels for a specific gene"

        return self.get_active_anotated().filter(genepanelentrysnapshot__gene__gene_symbol=gene_symbol)


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

    def __str__(self):
        return "{} v{}.{}".format(self.level4title.name, self.major_version, self.minor_version)

    def get_absolute_url(self):
        return reverse('panels:detail', args=(self.panel.pk,))

    @cached_property
    def stats(self):
        "Get stats for a panel, i.e. number of reviewers, genes, evaluated genes, etc"

        return GenePanelSnapshot.objects.filter(pk=self.pk).aggregate(
            number_of_reviewers=Count('genepanelentrysnapshot__evaluation__user__pk', distinct=True),
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
            )
        )

    @property
    def number_of_reviewers(self):
        "Get number of reviewers or set it if it's None"

        if self.current_number_of_reviewers is None:
            self.update_saved_stats()
        return self.current_number_of_reviewers

    @property
    def number_of_evaluated_genes(self):
        "Get number of evaluated genes or set it if it's None"

        if self.current_number_of_evaluated_genes is None:
            self.update_saved_stats()
        return self.current_number_of_evaluated_genes

    @property
    def number_of_genes(self):
        "Get number of genes or set it if it's None"

        if self.current_number_of_genes is None:
            self.update_saved_stats()
        return self.current_number_of_genes

    @property
    def version(self):
        return "{}.{}".format(self.major_version, self.minor_version)

    def increment_version(self, major=False, user=None, comment=None, ignore_gene=None):
        """Creates a new version of the panel.

        This script copies all genes, all information for these genes, and also
        you can add a comment and a user if it's a major vresion increment.

        DO NOT use it inside the methods of either genes or GenePanelSnapshot.
        This has weird behaviour as self refernces still goes to the previous
        snapshot and not the new one.
        """

        with transaction.atomic():
            current_genes = deepcopy(self.get_all_entries)

            self.pk = None

            if major:
                self.major_version += 1
                self.minor_version = 0
            else:
                self.minor_version += 1

            self.save()

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

            if self.panel.active_panel:
                del self.panel.active_panel

            if major:
                email_panel_promoted.delay(self.panel.pk)

                activity = "promoted panel to version {}".format(self.version)
                self.add_activity(user, '', activity)

                self.version_comment = "{} {} promoted panel to {}\n{}\n\n{}".format(
                    timezone.now().strftime('%Y-%m-%d %H:%M'),
                    user.get_reviewer_name(),
                    self.version,
                    comment,
                    self.version_comment if self.version_comment else ''
                )
                self.save()
            
            backup = PanelBackup()
            backup.import_panel(self)

            return self.panel.active_panel

    def update_saved_stats(self):
        "Get the new values from the database"

        if self.stats:
            del self.stats

        self.current_number_of_reviewers = self.stats.get('number_of_reviewers', 0)
        self.current_number_of_evaluated_genes = self.stats.get('number_of_evaluated_genes', 0)
        self.current_number_of_genes = self.stats.get('number_of_genes', 0)
        self.save(update_fields=[
            'current_number_of_evaluated_genes',
            'current_number_of_reviewers',
            'current_number_of_genes'
        ])

    @property
    def contributors(self):
        """Returns a tuple with user data

        Returns:
            A tuple with the user first and last name, email, and reviewer affiliation
        """

        return self.cached_entries\
            .distinct('evaluation__user')\
            .values_list(
                'evaluation__user__first_name',
                'evaluation__user__last_name',
                'evaluation__user__email',
                'evaluation__user__reviewer__affiliation',
                'evaluation__user__username'
            ).order_by('evaluation__user')

    def mark_genes_not_ready(self):
        for gene in self.cached_entries.all():
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
    def cached_entries(self):
        return self.genepanelentrysnapshot_set.all()

    @cached_property
    def current_genes(self):
        "Select and cache gene names"
        return list(self.current_genes_count.keys())

    @cached_property
    def current_genes_count(self):
        genes_list = [g.get('gene_symbol') for g in self.cached_entries.values_list('gene', flat=True)]
        return { gene: genes_list.count(gene) for gene in genes_list if gene }

    @cached_property
    def current_genes_duplicates(self):
        return [gene for gene in self.current_genes_count if self.current_genes_count[gene] > 1]

    @cached_property
    def get_all_entries(self):
        "Returns all Genes for this panel"

        return self.cached_entries\
            .annotate(
                evidences=ArrayAgg('evidence__pk', distinct=True),
                evaluations=ArrayAgg('evaluation__pk', distinct=True),
                gene_tags=ArrayAgg('tags__pk', distinct=True),
                tracks=ArrayAgg('track__pk', distinct=True),
                comment_pks=ArrayAgg('comments__pk', distinct=True)
            )

    @cached_property
    def get_all_entries_extra(self):
        "Get all genes and annotated info, speeds up loading time"

        return self.cached_entries\
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
    
    def get_gene_by_pk(self, gene_pk, prefetch_extra=False):
        "Get a gene for a specific pk."

        if prefetch_extra:
            return self.get_all_entries_extra.prefetch_related(
                'evaluation__comments',
                'evaluation__user__reviewer',
                'track',
                'track__user',
                'track__user__reviewer'
            ).get(pk=gene_pk)
        else:
            return self.get_all_entries.get(pk=gene_pk)

    def get_gene(self, gene_symbol, prefetch_extra=False):
        "Get a gene for a specific gene symbol."

        if prefetch_extra:
            return self.get_all_entries_extra.prefetch_related(
                'evaluation__comments',
                'evaluation__user__reviewer',
                'track',
                'track__user',
                'track__user__reviewer'
            ).get(gene__gene_symbol=gene_symbol)
        else:
            return self.get_all_entries.get(gene__gene_symbol=gene_symbol)

    def has_gene(self, gene_symbol):
        "Check if the panel has a gene with the provided gene symbol"

        return gene_symbol in [
            symbol.get('gene_symbol') for symbol in self.genepanelentrysnapshot_set.values_list('gene', flat=True)
        ]

    def clear_cache(self):
        if self.cached_entries:
            del self.__dict__['cached_entries']
        if self.current_genes_count:
            del self.__dict__['current_genes_count']
        if self.current_genes_duplicates:
            del self.__dict__['current_genes_duplicates']
        if self.current_genes:
            del self.__dict__['current_genes']
        if self.get_all_entries:
            del self.__dict__['get_all_entries']
        if self.get_all_entries_extra:
            del self.__dict__['get_all_entries_extra']

    def delete_gene(self, gene_symbol, increment=True):
        """Removes gene from a panel, but leaves it in the previous versions of the same panel"""

        if self.has_gene(gene_symbol):
            if increment:
                self = self.increment_version(ignore_gene=gene_symbol)
            else:
                self.get_all_entries.get(gene__gene_symbol=gene_symbol).delete()
                self.clear_cache()

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

        gene = self.cached_entries.model(
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
        if gene_data.get('comment'):
            comment = Comment.objects.create(
                user=user,
                comment=gene_data.get('comment')
            )
            gene.comments.add(comment)

        for source in gene_data.get('sources'):
            evidence = Evidence.objects.create(
                rating=5,
                reviewer=user.reviewer,
                name=source.strip()
            )
            gene.evidence.add(evidence)

        evidence_status = gene.evidence_status()
        track_created = TrackRecord.objects.create(
            gel_status=evidence_status,
            curator_status=0,
            user=user,
            issue_type=TrackRecord.ISSUE_TYPES.Created,
            issue_description="{} was created by {}".format(gene_core.gene_symbol, user.get_full_name())
        )
        gene.track.add(track_created)
        description = "{} was added to {} panel. Sources: {}".format(
            gene_core.gene_symbol,
            self.panel.name,
            ",".join(gene_data.get('sources'))
        )
        track_sources = TrackRecord.objects.create(
            gel_status=evidence_status,
            curator_status=0,
            user=user,
            issue_type=TrackRecord.ISSUE_TYPES.NewSource,
            issue_description=description
        )
        gene.track.add(track_sources)

        if gene_data.get('rating') or gene_data.get('comment'):
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
            if gene_data.get('comment'):
                evaluation.comments.add(comment)
            gene.evaluation.add(evaluation)
        self.clear_cache()

        self.add_activity(user, gene_symbol, "Added gene to panel")

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
                delete_evidences = [
                    source for source in evidences_names
                    if source not in Evidence.EXPERT_REVIEWS and not source in gene_data.get('sources')
                ]

                if not append_only:
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
            if moi and gene.moi != moi:
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
            elif gene_symbol.startswith("MT-"):
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
                logging.debug("Updating phenotypes for gene:{} in panel:{}".format(gene_symbol, self))
                gene.phenotypes = phenotypes

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
                track = TrackRecord.objects.create(
                    gel_status=status,
                    curator_status=0,
                    user=user,
                    issue_type=",".join([t[0] for t in tracks]),
                    issue_description="\n".join([t[1] for t in tracks])
                )
                gene.track.add(track)

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
                self.delete_gene(old_gene_symbol, increment=False)
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

    def copy_gene_reviews_from(self, genes, copy_from_panel):
        """Copy gene reviews from specified panel"""

        with transaction.atomic():
            current_genes = {gpes.gene.get('gene_symbol'): gpes for gpes in self.get_all_entries_extra.prefetch_related(
                'evidence__reviewer'
            )}
            copy_from_genes = {gpes.gene.get('gene_symbol'): gpes for gpes in copy_from_panel.get_all_entries_extra}

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

    def add_activity(self, user, gene_symbol, text):
        "Adds activity for this panel"

        Activity.objects.create(
            user=user,
            panel=self.panel,
            gene_symbol=gene_symbol,
            text=text
        )

    def tsv_file_header(self):
        return (
            "Gene_Symbol",
            "Sources(; separated)",
            "Level4",
            "Level3",
            "Level2",
            "Model_Of_Inheritance",
            "Phenotypes",
            "Omim",
            "Orphanet",
            "HPO",
            "Publications",
            "Description",
            "Flagged",
            "GEL_Status",
            "UserRatings_Green_amber_red",
            "version",
            "ready",
            "Mode of pathogenicity"
        )

    def tsv_file_export(self):
        panel_name = self.panel.name
        level3title = self.level4title.level3title
        level2title = self.level4title.level2title
        omim = ";".join(map(remove_non_ascii, self.level4title.omim))
        orphanet = ";".join(map(remove_non_ascii, self.level4title.orphanet))
        hpo = ";".join(map(remove_non_ascii, self.level4title.hpo))
        version = str(self.version)

        for gpentry in self.get_all_entries_extra:
            if gpentry.flagged:
                continue

            amber_perc, green_perc, red_prec = gpentry.aggregate_ratings()

            evidence = ";".join([evidence.name for evidence in gpentry.evidence.all()])
            yield (
                gpentry.gene.get('gene_symbol'),
                evidence,
                panel_name,
                level3title,
                level2title,
                gpentry.moi,
                ";".join(map(remove_non_ascii, gpentry.phenotypes)),
                omim,
                orphanet,
                hpo,
                ";".join(map(remove_non_ascii, gpentry.publications)),
                "",
                str(gpentry.flagged),
                str(gpentry.saved_gel_status),
                ";".join(map(str, [green_perc, amber_perc, red_prec])),
                version,
                gpentry.ready,
                gpentry.mode_of_pathogenicity
            )
