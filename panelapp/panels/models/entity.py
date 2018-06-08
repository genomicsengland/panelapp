"""Abstract class for panels entities

Author: Oleg Gerasimenko

(c) 2018 Genomics England
"""

from model_utils import Choices

from .evaluation import Evaluation
from .comment import Comment
from .trackrecord import TrackRecord
from .evidence import Evidence
from panels.templatetags.panel_helpers import get_gene_list_data
from panels.templatetags.panel_helpers import GeneDataType


class AbstractEntity:
    """Abstract methods which are used by the entity classes: Genes, STRs"""

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

    def approve_entity(self):
        self.flagged = False
        self.save()

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

    def is_str(self):
        return self.entity_type == 'str'

    def is_gene(self):
        return self.entity_type == 'gene'

    @property
    def status(self):
        """Save gel_status in the gene panel snapshot if saved_gel_status isn't set"""

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

    def is_reviewd_by_user(self, user):
        """Check if the entity was reviewed by the specific user"""

        return True if self.review_by_user(user) else False

    def review_by_user(self, user):
        """Check if user evaluated this entity, returns either the evaluation
        or None"""

        return self.evaluation.filter(user=user).first()

    def clear_expert_evidence(self, evidence):
        """Remove expert evidences. This is used when we set the new expert evidence"""

        evidences = self.evidence.filter(name=evidence)
        if len(evidences) > 0:
            evidences.delete()
            return True
        else:
            return False

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
        self.panel.add_activity(user, 'added comment: {}'.format(comment.comment), self)

    def delete_evaluation(self, evaluation_pk, user=None):
        self.evaluation.get(pk=evaluation_pk).delete()
        if user:
            self.panel.add_activity(user, 'deleted their review', self)

    def delete_comment(self, comment_pk, user=None):
        evaluation = self.evaluation.get(comments__pk=comment_pk)
        evaluation.comments.get(pk=comment_pk).delete()
        if user:
            self.panel.add_activity(user, 'deleted their comment', self)

    def edit_comment(self, comment_pk, new_comment, user=None):
        evaluation = self.evaluation.get(comments__pk=comment_pk)
        comment = evaluation.comments.get(pk=comment_pk)
        old_comment = comment.comment
        comment.comment = new_comment
        comment.save()
        if user:
            self.panel.add_activity(user, 'changed review comment from: {}; to: {}'.format(old_comment, new_comment), self)

    def aggregate_ratings(self):
        """Gets stats about the gene, i.e. % of green, red, amber evaluations"""

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

    def get_review_comments(self):
        """Get review comments in a chronological order.

        Used for list of review comments

        Returns:
            QuerySet: List of evaluation comments
        """

        return Comment.objects.filter(evaluation__pk__in=self.evaluation.values_list('pk', flat=True)).prefetch_related(
            'user',
            'user__reviewer'
        )

    def clear_evidences(self, user, evidence=None):
        """Remove sources from this entity. If `evidence` argument provided, check only that source"""

        description = None

        if evidence:
            evidences = self.evidence.filter(name=evidence)
            if len(evidences) > 0:
                for evidence in evidences:
                    if evidence.is_GEL:
                        self.evidence.remove(evidence)

                        description = "Source: {} was removed from {}".format(
                            evidence,
                            self.label
                        )
            else:
                return False
        else:
            for evidence in self.evidence.all():
                if evidence.is_GEL:
                    self.evidence.remove(evidence)

            description = "All sources for {} were removed".format(
                self.label
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
            self.panel.add_activity(user, description, self)

        return True

    def set_rating(self, user, status=None):
        """This method is used when a GeL curator changes the rating via website"""

        if not status:
            status = self.status

        [self.clear_expert_evidence(e) for e in Evidence.EXPERT_REVIEWS]

        if isinstance(status, str):
            status = int(status)

        if status > 2:
            evidence = Evidence.objects.create(name="Expert Review Green", rating=5, reviewer=user.reviewer)
            issue_description = "{} has been classified as Green List (High Evidence).".format(self.label.capitalize())
            self.flagged = False
            self.evidence.add(evidence)
        elif status == 2:
            evidence = Evidence.objects.create(name="Expert Review Amber", rating=5, reviewer=user.reviewer)
            issue_description = "{} has been classified as Amber List (Moderate Evidence).".format(self.label.capitalize())
            self.flagged = False
            self.evidence.add(evidence)
        elif status == 1:
            evidence = Evidence.objects.create(name="Expert Review Red", rating=5, reviewer=user.reviewer)
            issue_description = "{} has been classified as Red List (Low Evidence).".format(self.label.capitalize())
            self.evidence.add(evidence)
            self.flagged = False
        elif status == 0:
            evidence = Evidence.objects.create(name="Expert Review Removed", rating=5, reviewer=user.reviewer)
            issue_description = "{} has been removed from the panel.".format(self.label.capitalize())
            self.evidence.add(evidence)
            self.flagged = True
        else:
            return False

        track = TrackRecord.objects.create(
            gel_status=status,
            curator_status=0,
            user=user,
            issue_type=TrackRecord.ISSUE_TYPES.EntityClassifiedbyGenomicsEnglandCurator,
            issue_description=issue_description
        )
        self.track.add(track)
        self.panel.add_activity(user, issue_description, self)
        self.saved_gel_status = status
        self.save()
        return True

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

        self.panel.add_activity(user, "marked {} as ready".format(self.label), self)
        self.save()

    def update_moi(self, moi, user, moi_comment=None):
        old_moi = self.moi
        self.moi = moi
        self.save()

        description = "Mode of inheritance for {} was changed from {} to {}".format(
            self.label,
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
        self.panel.add_activity(user, description, self)

        if moi_comment:
            self.add_review_comment(
                user,
                "Comment on mode of inheritance: {}".format(moi_comment)
            )

    def update_pathogenicity(self, mop, user, mop_comment=None):
        self.mode_of_pathogenicity = mop
        self.save()

        description = "Mode of pathogenicity for {} was changed to {}".format(self.label, mop)
        track = TrackRecord.objects.create(
            gel_status=self.status,
            curator_status=0,
            user=user,
            issue_type=TrackRecord.ISSUE_TYPES.SetModeofPathogenicity,
            issue_description=description
        )
        self.track.add(track)
        self.panel.add_activity(user, description, self)

        if mop_comment:
            self.add_review_comment(
                user,
                "Comment on mode of pathogenicity: {}".format(mop_comment)
            )

    def update_phenotypes(self, phenotypes, user, phenotypes_comment=None):
        self.phenotypes = phenotypes
        self.save()

        description = "Phenotypes for {} were set to {}".format(self.label, "; ".join(phenotypes))
        track = TrackRecord.objects.create(
            gel_status=self.status,
            curator_status=0,
            user=user,
            issue_type=TrackRecord.ISSUE_TYPES.SetPhenotypes,
            issue_description=description
        )
        self.track.add(track)
        self.panel.add_activity(user, description, self)

        if phenotypes_comment:
            self.add_review_comment(
                user,
                "Comment on phenotypes: {}".format(phenotypes_comment)
            )

    def update_publications(self, publications, user, publications_comment=None):
        self.publications = publications
        self.save()

        description = "Publications for {} were set to {}".format(self.label, "; ".join(publications))
        track = TrackRecord.objects.create(
            gel_status=self.status,
            curator_status=0,
            user=user,
            issue_type=TrackRecord.ISSUE_TYPES.SetPublications,
            issue_description=description
        )
        self.track.add(track)
        self.panel.add_activity(user, description, self)

        if publications_comment:
            self.add_review_comment(
                user,
                "Comment on publications: {}".format(publications_comment)
            )

    def update_rating(self, rating, user, rating_comment=None):
        rating_set = self.set_rating(user, rating)
        if not rating_set:
            return

        if rating_comment:
            self.add_review_comment(
                user,
                "Comment on list classification: {}".format(rating_comment)
            )

        human_status = get_gene_list_data(self, GeneDataType.LONG.value)

        self.panel.add_activity(user, "classified {} as {}".format(self.label, human_status), self)

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
            if current_diagnostic and evaluation.current_diagnostic != current_diagnostic:
                changed = True
                evaluation.current_diagnostic = current_diagnostic

            clinically_relevant = evaluation_data.get('clinically_relevant')
            if self.is_str() and evaluation.clinically_relevant != clinically_relevant:
                changed = True
                evaluation.clinically_relevant = clinically_relevant

            evaluation.version = self.panel.version

            activity_text = None

            if changed:
                activity_text = "edited their review of {}".format(self.label)
            elif evaluation_data.get('comment'):
                activity_text = "commented on {}".format(self.label)

            if activity_text:
                self.panel.add_activity(user, activity_text, self)

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
                clinically_relevant=evaluation_data.get('clinically_relevant'),
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
                activity_text = "commented on {}".format(self.label)
            else:
                activity_text = "reviewed {}".format(self.label)

            self.panel.add_activity(user, activity_text, self)

            return evaluation
