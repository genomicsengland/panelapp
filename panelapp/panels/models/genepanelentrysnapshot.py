from django.db import models
from django.db.models import Count
from django.db.models import Subquery
from django.urls import reverse

from django.core.serializers.json import DjangoJSONEncoder
from django.contrib.postgres.fields import JSONField
from django.contrib.postgres.fields import ArrayField
from model_utils import Choices
from model_utils.models import TimeStampedModel

from .gene import Gene
from .evidence import Evidence
from .evaluation import Evaluation
from .trackrecord import TrackRecord
from .comment import Comment
from .tag import Tag
from .genepanelsnapshot import GenePanelSnapshot
from panels.templatetags.panel_helpers import get_gene_list_data
from panels.templatetags.panel_helpers import GeneDataType


class GenePanelEntrySnapshotManager(models.Manager):
    """Objects manager for GenePanelEntrySnapshot."""

    def get_latest_ids(self, deleted=False):
        """Get GenePanelSnapshot ids"""

        qs = super().get_queryset()
        if not deleted:
            qs = qs.exclude(panel__panel__deleted=True)

        return qs.distinct('panel__panel__pk')\
            .values_list('panel__pk', flat=True)\
            .order_by('panel__panel__pk', '-panel__major_version', '-panel__minor_version')

    def get_active(self, deleted=False, gene_symbol=None, pks=None):
        """Get active Gene Entry Snapshots"""

        if pks:
            qs = super().get_queryset().filter(panel__pk__in=pks)
        else:
            qs = super().get_queryset().filter(panel__pk__in=Subquery(self.get_latest_ids(deleted)))
        if gene_symbol:
            qs = qs.filter(gene_core__gene_symbol=gene_symbol)

        return qs.annotate(
                number_of_reviewers=Count('evaluation__user', distinct=True),
                number_of_evaluated_genes=Count('evaluation'),
                number_of_genes=Count('pk'),
            )\
            .prefetch_related('evaluation', 'tags', 'evidence', 'panel', 'panel__level4title', 'panel__panel')\
            .order_by('panel__pk', '-panel__major_version', '-panel__minor_version')

    def get_gene_panels(self, gene_symbol, deleted=False, pks=None):
        """Get panels for the specified gene"""

        return self.get_active(deleted=deleted, gene_symbol=gene_symbol, pks=pks)


class GenePanelEntrySnapshot(TimeStampedModel):
    PENETRANCE = Choices(
        ("unknown", "unknown"),
        ("Complete", "Complete"),
        ("Incomplete", "Incomplete"),
    )

    GEL_STATUS = Choices(
        (3, "Green List (high evidence)"),
        (2, "Amber List (moderate evidence)"),
        (1, "Red List (low evidence)"),
        (0, "No List (delete)"),
    )

    class Meta:
        get_latest_by = "created"
        ordering = ['-saved_gel_status', ]
        indexes = [
            models.Index(fields=['panel_id']),
            models.Index(fields=['gene_core_id'])
        ]

    panel = models.ForeignKey(GenePanelSnapshot)
    gene = JSONField(encoder=DjangoJSONEncoder)  # copy data from Gene.dict_tr
    gene_core = models.ForeignKey(Gene)  # reference to the original Gene
    evidence = models.ManyToManyField(Evidence)
    evaluation = models.ManyToManyField(Evaluation, db_index=True)
    moi = models.CharField("Mode of inheritance", choices=Evaluation.MODES_OF_INHERITANCE, max_length=255)
    penetrance = models.CharField(choices=PENETRANCE, max_length=255, blank=True, null=True)
    track = models.ManyToManyField(TrackRecord)
    publications = ArrayField(models.TextField(), blank=True, null=True)
    phenotypes = ArrayField(models.TextField(), blank=True, null=True)
    tags = models.ManyToManyField(Tag)
    flagged = models.BooleanField(default=False)
    ready = models.BooleanField(default=False)
    comments = models.ManyToManyField(Comment)
    mode_of_pathogenicity = models.CharField(
        choices=Evaluation.MODES_OF_PATHOGENICITY,
        max_length=255,
        null=True,
        blank=True
    )
    saved_gel_status = models.IntegerField(null=True, db_index=True)

    objects = GenePanelEntrySnapshotManager()

    def __str__(self):
        return "Panel: {} Gene: {}".format(self.panel.panel.name, self.gene.get('gene_symbol'))

    def get_absolute_url(self):
        """Returns absolute url for this gene in a panel"""

        return reverse('panels:evaluation', args=(self.panel.panel.pk, self.gene.get('gene_symbol')))

    @property
    def status(self):
        "Save gel_status in the gene panel snapshot if saved_gel_status isn't set"

        if self.saved_gel_status is None:
            self.status = self.evidence_status()
            self.save()
        return self.saved_gel_status

    @status.setter
    def status(self, value):
        self.saved_gel_status = value

    @status.deleter
    def status(self):
        self.saved_gel_status = None

    def evidence_status(self, update=False):
        """ This is a refactored `get_gel_status` function.

        It goes through evidences, check if they are valid or were provided by
        curators, and returns the status.
        This status is later used to determine the colour on the frontend and APIs
        """

        if self.flagged:
            return 0

        gel_status = 0
        has_gel_reviews = False
        for evidence in self.evidence.all():
            if evidence.is_GEL:
                has_gel_reviews = True
                if evidence.name in evidence.EXPERT_REVIEWS:
                    if update:
                        self.saved_gel_status = evidence.EXPERT_REVIEWS.get(evidence.name)
                        self.save()
                    return evidence.EXPERT_REVIEWS.get(evidence.name)
                if evidence.name in evidence.HIGH_CONFIDENCE_SOURCES and evidence.rating > 3:
                    gel_status += 1

        if has_gel_reviews and gel_status == 0:
            gel_status = 1

        if update:
            self.saved_gel_status = gel_status
            self.save()

        return gel_status

    def is_reviewd_by_user(self, user):
        "Check if the gene was reviewed by the specific user"

        return True if self.review_by_user(user) else False

    def review_by_user(self, user):
        """Check if user evaluated this gene, returns either the evaluation
        or None"""

        return self.evaluation.filter(user=user).first()

    def clear_evidences(self, user, evidence=None):
        "Remove sources from this gene. If `evidence` argument provided, check only that source"

        description = None

        if evidence:
            evidences = self.evidence.filter(name=evidence)
            if len(evidences) > 0:
                for evidence in evidences:
                    if evidence.is_GEL:
                        self.evidence.remove(evidence)

                        description = "{} Source: {} was removed from gene: {}".format(
                            self.gene.get('gene_symbol'),
                            evidence,
                            self.gene.get('gene_symbol')
                        )
            else:
                return False
        else:
            for evidence in self.evidence.all():
                if evidence.is_GEL:
                    self.evidence.remove(evidence)

            description = "{} All sources for gene: {} were removed".format(
                self.gene.get('gene_symbol'),
                self.gene.get('gene_symbol')
            )

        evidence_status = self.evidence_status(update=True)

        if description:
            track_sources = TrackRecord.objects.create(
                gel_status=evidence_status,
                curator_status=0,
                user=user,
                issue_type=TrackRecord.ISSUE_TYPES.ClearSources,
                issue_description=description
            )
            self.track.add(track_sources)

        return True

    def clear_expert_evidence(self, evidence):
        "Remove expert evidences. This is used when we set the new expert evidence"

        evidences = self.evidence.filter(name=evidence)
        if len(evidences) > 0:
            evidences.delete()
            return True
        else:
            return False

    def set_rating(self, user, status=None):
        "This method is used when a GeL curator changes the rating via website"

        if not status:
            status = self.status

        [self.clear_expert_evidence(e) for e in Evidence.EXPERT_REVIEWS]

        if isinstance(status, str):
            status = int(status)

        if status > 2:
            evidence = Evidence.objects.create(name="Expert Review Green", rating=5, reviewer=user.reviewer)
            issue_description = "This gene has been classified as Green List (High Evidence)."
            self.flagged = False
            self.evidence.add(evidence)
        elif status == 2:
            evidence = Evidence.objects.create(name="Expert Review Amber", rating=5, reviewer=user.reviewer)
            issue_description = "This gene has been classified as Amber List (Moderate Evidence)."
            self.flagged = False
            self.evidence.add(evidence)
        elif status == 1:
            evidence = Evidence.objects.create(name="Expert Review Red", rating=5, reviewer=user.reviewer)
            issue_description = "This gene has been classified as Red List (Low Evidence)."
            self.evidence.add(evidence)
            self.flagged = False
        elif status == 0:
            evidence = Evidence.objects.create(name="Expert Review Removed", rating=5, reviewer=user.reviewer)
            issue_description = "This gene has been removed from the panel."
            self.evidence.add(evidence)
            self.flagged = True
        else:
            return False

        track = TrackRecord.objects.create(
            gel_status=status,
            curator_status=0,
            user=user,
            issue_type=TrackRecord.ISSUE_TYPES.GeneClassifiedbyGenomicsEnglandCurator,
            issue_description=issue_description
        )
        self.track.add(track)
        self.saved_gel_status = status
        self.save()
        return True

    def approve_gene(self):
        self.flagged = False
        self.save()

    def mark_as_ready(self, user, ready_comment):
        self.ready = True

        status = self.status
        rating_set = self.set_rating(user, status)
        if not rating_set:
            return

        if ready_comment:
            self.add_review_comment(
                user,
                "Comment when marking as ready: {}".format(ready_comment)
            )

        self.panel.add_activity(
            user,
            self.gene.get('gene_symbol'),
            "marked {} as ready".format(self.gene.get('gene_symbol'))
        )

        self.save()

    def update_moi(self, moi, user, moi_comment=None):
        old_moi = self.moi
        self.moi = moi
        self.save()

        description = "Mode of inheritance for {} was changed from {} to {}".format(
            self.gene.get('gene_symbol'),
            old_moi,
            moi
        )
        track = TrackRecord.objects.create(
            gel_status=self.status,
            curator_status=0,
            user=user,
            issue_type=TrackRecord.ISSUE_TYPES.SetModeofInheritance,
            issue_description=description
        )
        self.track.add(track)

        if moi_comment:
            self.add_review_comment(
                user,
                "Comment on mode of inheritance: {}".format(moi_comment)
            )

    def update_pathogenicity(self, mop, user, mop_comment=None):
        self = self.panel.get_gene(self.gene.get('gene_symbol'))
        self.mode_of_pathogenicity = mop
        self.save()

        description = "Mode of pathogenicity for {} was changed to {}".format(self.gene.get('gene_symbol'), mop)
        track = TrackRecord.objects.create(
            gel_status=self.status,
            curator_status=0,
            user=user,
            issue_type=TrackRecord.ISSUE_TYPES.SetModeofPathogenicity,
            issue_description=description
        )
        self.track.add(track)

        if mop_comment:
            self.add_review_comment(
                user,
                "Comment on mode of pathogenicity: {}".format(mop_comment)
            )

    def update_phenotypes(self, phenotypes, user, phenotypes_comment=None):
        self = self.panel.get_gene(self.gene.get('gene_symbol'))
        self.phenotypes = phenotypes
        self.save()

        description = "Phenotypes for {} were set to {}".format(self.gene.get('gene_symbol'), "; ".join(phenotypes))
        track = TrackRecord.objects.create(
            gel_status=self.status,
            curator_status=0,
            user=user,
            issue_type=TrackRecord.ISSUE_TYPES.SetPhenotypes,
            issue_description=description
        )
        self.track.add(track)

        if phenotypes_comment:
            self.add_review_comment(
                user,
                "Comment on phenotypes: {}".format(phenotypes_comment)
            )

    def update_publications(self, publications, user, publications_comment=None):
        self = self.panel.get_gene(self.gene.get('gene_symbol'))
        self.publications = publications
        self.save()

        gene = self.gene.get('gene_symbol')
        description = "Publications for {} were set to {}".format(gene, "; ".join(publications))
        track = TrackRecord.objects.create(
            gel_status=self.status,
            curator_status=0,
            user=user,
            issue_type=TrackRecord.ISSUE_TYPES.SetPublications,
            issue_description=description
        )
        self.track.add(track)

        if publications_comment:
            self.add_review_comment(
                user,
                "Comment on publications: {}".format(publications_comment)
            )

    def add_review_comment(self, user, comment):
        comment = Comment.objects.create(
            user=user,
            comment=comment
        )

        evaluation = self.review_by_user(user)
        if not evaluation:
            evaluation = Evaluation.objects.create(
                user=user,
                version=self.panel.version
            )
            self.evaluation.add(evaluation)
        evaluation.comments.add(comment)

    def update_rating(self, rating, user, rating_comment=None):
        gene = self.gene.get('gene_symbol')
        self = self.panel.get_gene(gene)

        rating_set = self.set_rating(user, rating)
        if not rating_set:
            return

        if rating_comment:
            self.add_review_comment(
                user,
                "Comment on list classification: {}".format(rating_comment)
            )

        human_status = get_gene_list_data(self, GeneDataType.LONG.value)
        self.panel.add_activity(user, gene, "classified {} as {}".format(gene, human_status))

    def delete_evaluation(self, evaluation_pk):
        self.evaluation.get(pk=evaluation_pk).delete()

    def delete_comment(self, comment_pk):
        evaluation = self.evaluation.get(comments__pk=comment_pk)
        evaluation.comments.get(pk=comment_pk).delete()

    def edit_comment(self, comment_pk, new_comment):
        evaluation = self.evaluation.get(comments__pk=comment_pk)
        comment = evaluation.comments.get(pk=comment_pk)
        comment.comment = new_comment
        comment.save()

    def aggregate_ratings(self):
        "Gets stats about the gene, i.e. % of green, red, amber evaluations"

        green, red, amber = 0, 0, 0
        for ev in self.evaluation.all():
            if ev.rating == Evaluation.RATINGS.GREEN:
                green += 1
            elif ev.rating == Evaluation.RATINGS.RED:
                red += 1
            elif ev.rating == Evaluation.RATINGS.AMBER:
                amber += 1

        total = green + red + amber
        if green + red + amber > 0:
            green_perc = round(green * 100.0 / (total))
            red_prec = round(red * 100.0 / (total))
            amber_perc = round(amber * 100.0 / (total))
        else:
            green_perc = 0
            red_prec = 0
            amber_perc = 0

        return amber_perc, green_perc, red_prec

    def update_evaluation(self, user, evaluation_data):
        """
        This method adds or updates an evaluation in case the user has already
        added an evaluation in the past. In this case it just checks the new values
        and adds them instead. If the value isn't set, then we remove it.

        args:
            user (User): User that this evaluation belongs to
            evaluation_data (dict): Dictionary with the new values for this evaluation,
                it will use following parameters:

                - comment
                - mode_of_pathogenicity
                - publications
                - phenotypes
                - moi
                - current_diagnostic
                - rating

        returns:
            Evaluation: new or updated evaluation
        """

        try:
            evaluation = self.evaluation.get(user=user)

            changed = False

            if evaluation_data.get('comment'):
                comment = Comment.objects.create(
                    user=user,
                    comment=evaluation_data.get('comment')
                )
                evaluation.comments.add(comment)
            
            rating = evaluation_data.get('rating')
            if rating and evaluation.rating != rating:
                changed = True
                evaluation.rating = rating

            mop = evaluation_data.get('mode_of_pathogenicity')
            if mop and evaluation.mode_of_pathogenicity != mop:
                changed = True
                evaluation.mode_of_pathogenicity = mop

            publications = evaluation_data.get('publications')
            if publications and evaluation.publications != publications:
                changed = True
                evaluation.publications = publications

            phenotypes = evaluation_data.get('phenotypes')
            if phenotypes and evaluation.phenotypes != phenotypes:
                changed = True
                evaluation.phenotypes = phenotypes

            moi = evaluation_data.get('moi')
            if moi and evaluation.moi != moi:
                changed = True
                evaluation.moi = moi

            current_diagnostic = evaluation_data.get('current_diagnostic')
            if moi and evaluation.current_diagnostic != current_diagnostic:
                changed = True
                evaluation.current_diagnostic = current_diagnostic

            evaluation.version = self.panel.version

            if changed:
                activity_text = "commented on {}".format(self.gene.get('gene_symbol'))
                self.panel.add_activity(user, self.gene.get('gene_symbol'), activity_text)
            elif evaluation_data.get('comment'):
                activity_text = "edited their review of {}".format(self.gene.get('gene_symbol'))
                self.panel.add_activity(user, self.gene.get('gene_symbol'), activity_text)

            evaluation.save()
            return evaluation

        except Evaluation.DoesNotExist:
            evaluation = Evaluation.objects.create(
                user=user,
                rating=evaluation_data.get('rating'),
                mode_of_pathogenicity=evaluation_data.get('mode_of_pathogenicity'),
                publications=evaluation_data.get('publications'),
                phenotypes=evaluation_data.get('phenotypes'),
                moi=evaluation_data.get('moi'),
                current_diagnostic=evaluation_data.get('current_diagnostic'),
                version=self.panel.version
            )
            self.evaluation.add(evaluation)

            if evaluation_data.get('comment'):
                comment = Comment.objects.create(
                    user=user,
                    comment=evaluation_data.get('comment')
                )
                evaluation.comments.add(comment)
            if evaluation.is_comment_without_review():
                activity_text = "commented on {}".format(self.gene.get('gene_symbol'))
                self.panel.add_activity(user, self.gene.get('gene_symbol'), activity_text)
            else:
                activity_text = "reviewed {}".format(self.gene.get('gene_symbol'))
                self.panel.add_activity(user, self.gene.get('gene_symbol'), activity_text)

            return evaluation

    def dict_tr(self):
        return {
            "gene": self.gene,
            "evidence": [evidence.dict_tr() for evidence in self.evidence.all()],
            "evaluation": [evaluation.dict_tr() for evaluation in self.evaluation.all()],
            "track": [track.dict_tr() for track in self.track.all()],
            "moi": self.moi,
            "publications": self.publications,
            "phenotypes": self.phenotypes,
            "flagged": self.flagged,
            "mode_of_pathogenicity": self.mode_of_pathogenicity,
            "penetrance": self.penetrance,
            "tags": [tag.name for tag in self.tags.all()]
        }

    def get_form_initial(self):
        """Since we create a new version every time we want to update something this method
        gets the initial data for the form.
        """

        return {
            "gene": self.gene_core,
            "gene_json": self.gene,
            "gene_name": self.gene.get('gene_name'),
            "source": [e.name for e in self.evidence.all() if e.is_GEL],
            "tags": self.tags.all(),
            "publications": self.publications,
            "phenotypes": self.phenotypes,
            "mode_of_pathogenicity": self.mode_of_pathogenicity,
            "moi": self.moi,
            "penetrance": self.penetrance
        }

    def get_review_comments(self):
        """Get review comments in a chronological order.

        Used for list of review comments

        Returns QuerySet
        """

        return Comment.objects.filter(evaluation__pk__in=self.evaluation.values_list('pk', flat=True))
