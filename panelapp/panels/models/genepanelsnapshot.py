import logging
from django.db import models
from django.db.models import Count
from django.db.models import Case
from django.db.models import When
from django.db.models import Subquery
from django.contrib.postgres.fields import ArrayField
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


class GenePanelSnapshotManager(models.Manager):
    def get_latest_ids(self):
        "Get latest versions for GenePanelsSnapshots"

        return super().get_queryset()\
            .distinct('panel__pk')\
            .values('pk')\
            .order_by('panel__pk', '-major_version', '-minor_version')

    def get_active(self, all=False):
        "Get all active panels"

        qs = super().get_queryset()

        if not all:
            qs = qs.filter(panel__approved=True)

        return qs.filter(pk__in=Subquery(self.get_latest_ids()))\
            .prefetch_related('panel', 'level4title')\
            .order_by('panel__name', '-major_version', '-minor_version')

    def get_active_anotated(self, all=False):
        "This method adds additional values to the queryset, such as number_of_genes, etc and returns active panels"

        return self.get_active(all)\
            .annotate(
                number_of_reviewers=Count('genepanelentrysnapshot__evaluation__user', distinct=True),
                number_of_evaluated_genes=Count(Case(
                    # Count unique genes if that gene has more than 1 evaluation
                    When(
                        genepanelentrysnapshot__evaluation__isnull=False,
                        then=models.F('genepanelentrysnapshot__pk')
                    )
                ), distinct=True),
                number_of_genes=Count('genepanelentrysnapshot', distinct=True),
            )

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
        ordering = ['-major_version', '-minor_version', '-created']

    objects = GenePanelSnapshotManager()

    level4title = models.ForeignKey(Level4Title)
    panel = models.ForeignKey(GenePanel)
    major_version = models.IntegerField(default=0)
    minor_version = models.IntegerField(default=0)
    version_comment = models.TextField(null=True)
    old_panels = ArrayField(models.CharField(max_length=255), blank=True, null=True)

    @cached_property
    def stats(self):
        "Get stats for a panel, i.e. number of reviewers, genes, evaluated genes, etc"

        return self.genepanelentrysnapshot_set.aggregate(
            number_of_reviewers=Count('evaluation__user', distinct=True),
            number_of_evaluated_genes=Count(Case(When(evaluation__isnull=False, then=models.F('pk'))), distinct=True),
            number_of_genes=Count('pk'),
            number_of_ready_genes=Count(Case(When(ready=True, then=models.F('pk'))), distinct=True),
            number_of_green_genes=Count(Case(When(saved_gel_status__gte=3, then=models.F('pk'))), distinct=True)
        )

    def __str__(self):
        return "Panel {} v{}.{}".format(self.level4title.name, self.major_version, self.minor_version)

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
        current_genes = self.get_all_entries

        self.pk = None

        if major:
            self.major_version += 1
            self.minor_version = 0
        else:
            self.minor_version += 1

        self.save()

        for gene in current_genes:
            if ignore_gene and ignore_gene == gene.gene.get('gene_symbol'):
                continue

            evidences = gene.evidence.all()
            evaluations = gene.evaluation.all()
            tracks = gene.track.all()
            tags = gene.tags.all()
            comments = gene.comments.all()

            gene.pk = None
            gene.panel = self
            if major:
                gene.ready = False
            gene.save()

            for evidence in evidences:
                gene.evidence.add(evidence)

            for evaluation in evaluations:
                gene.evaluation.add(evaluation)

            for track in tracks:
                gene.track.add(track)

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

            for tag in tags:
                gene.tags.add(tag)

            for comment in comments:
                gene.comments.add(comment)

        if major:
            email_panel_promoted.delay(self.pk)

            activity = "promoted panel to version {}".format(self.version)
            self.add_activity(user, '', activity)

            self.version_comment = comment

        del self.get_all_entries
        return self

    @property
    def contributors(self):
        """Returns a tuple with user data

        Returns:
            A tuple with the user first and last name, email, and reviewer affiliation
        """

        return self.genepanelentrysnapshot_set\
            .distinct('evaluation__user')\
            .values_list(
                'evaluation__user__first_name',
                'evaluation__user__last_name',
                'evaluation__user__email',
                'evaluation__user__reviewer__affiliation'
            ).order_by('evaluation__user')

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
        "Returns all Genes for this panel"

        return self.genepanelentrysnapshot_set\
            .prefetch_related('evidence', 'evaluation', 'tags')\
            .annotate(
                number_of_green_evaluations=Count(Case(When(
                    evaluation__rating="GREEN", then=models.F('evaluation__pk'))
                ), distinct=True),
                number_of_amber_evaluations=Count(Case(When(
                    evaluation__rating="AMBER", then=models.F('evaluation__pk'))
                ), distinct=True),
                number_of_red_evaluations=Count(Case(When(
                    evaluation__rating="RED", then=models.F('evaluation__pk'))
                ), distinct=True),
            )\
            .order_by('-saved_gel_status', 'gene_core__gene_symbol', '-created')

    def get_gene(self, gene_symbol):
        "Get a gene for a specific gene symbol."

        return self.get_all_entries.prefetch_related(
            'evaluation__comments',
            'evaluation__user',
            'evaluation__user__reviewer',
            'track',
            'track__user',
            'track__user__reviewer'
        ).get(gene__gene_symbol=gene_symbol)

    def has_gene(self, gene_symbol):
        "Check if the panel has a gene with the provided gene symbol"

        return True if self.get_all_entries.filter(gene__gene_symbol=gene_symbol).count() > 0 else False

    def delete_gene(self, gene_symbol, increment=True):
        """Removes gene from a panel, but leaves it in the previous versions of the same panel"""

        if self.has_gene(gene_symbol):
            if increment:
                self.increment_version(ignore_gene=gene_symbol)
            else:
                self.get_all_entries.get(gene__gene_symbol=gene_symbol).delete()
                del self.get_all_entries
            return True
        else:
            return False

    def add_gene(self, user, gene_symbol, gene_data):
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

        self = self.increment_version()

        gene_core = Gene.objects.get(gene_symbol=gene_symbol)
        gene_info = gene_core.dict_tr()

        gene = self.genepanelentrysnapshot_set.model(
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
        gene.evidence_status(update=True)
        return gene

    def update_gene(self, user, gene_symbol, gene_data):
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
            evidences_names = [ev.name.strip() for ev in gene.evidence.all()]

            logging.debug("Updating evidences_names for gene:{} in panel:{}".format(gene_symbol, self))
            if gene_data.get('sources'):
                for source in gene_data.get('sources'):
                    cleaned_source = source.strip()
                    if cleaned_source not in evidences_names:
                        logging.debug("Adding new evidence:{} for gene:{} panel:{}".format(
                            cleaned_source, gene_symbol, self
                        ))
                        evidence = Evidence.objects.create(
                            name=cleaned_source,
                            rating=5,
                            reviewer=user.reviewer
                        )
                        gene.evidence.add(evidence)

                        description = "{} was added to {} panel. Source: {}".format(
                            gene_symbol,
                            self.panel.name,
                            cleaned_source
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
                diff = set(phenotypes).difference(gene.phenotypes)
                logging.debug("Updating phenotypes for gene:{} in panel:{}".format(gene_symbol, self))
                for p in diff:
                    gene.phenotypes.append(p)

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
                evaluations = gene.evaluation.all()
                tracks = gene.track.all()
                tags = gene.tags.all()
                comments = gene.comments.all()

                new_gpes = gene
                new_gpes.gene_core = new_gene
                new_gpes.gene = new_gene.dict_tr()
                new_gpes.pk = None
                new_gpes.panel = self
                new_gpes.save()

                for evidence in evidences:
                    new_gpes.evidence.add(evidence)

                for evaluation in evaluations:
                    new_gpes.evaluation.add(evaluation)

                for track in tracks:
                    new_gpes.track.add(track)

                for tag in tags:
                    new_gpes.tags.add(tag)

                for comment in comments:
                    new_gpes.comments.add(comment)

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
            elif gene.gene.get('gene_name') != gene_name:
                logging.debug("Updating gene_name for gene:{} in panel:{}".format(gene_symbol, self))
                gene.gene['gene_name'] = gene_name
                gene.save()
            else:
                gene.save()
            return gene
        else:
            return False

    def add_activity(self, user, gene_symbol, text):
        "Adds activity for this panel"

        Activity.objects.create(
            user=user,
            panel=self.panel,
            gene_symbol=gene_symbol,
            text=text
        )
