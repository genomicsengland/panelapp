import json
import factory
from random import randint
from panels.models import Gene
from panels.models import GenePanelEntrySnapshot
from panels.models import Evidence
from panels.models import Evaluation
from panels.models import TrackRecord
from panels.models import Tag
from panels.models import Comment
from panels.models import Level4Title
from panels.models import GenePanel
from panels.models import GenePanelSnapshot


class Level4TitleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Level4Title

    name = factory.Faker('sentence', nb_words=6, variable_nb_words=True)
    description = factory.Faker('sentence', nb_words=6, variable_nb_words=True)
    level3title = factory.Faker('sentence', nb_words=6, variable_nb_words=True)
    level2title = factory.Faker('sentence', nb_words=6, variable_nb_words=True)
    omim = factory.Faker('sentences', nb=3)
    orphanet = factory.Faker('sentences', nb=3)
    hpo = factory.Faker('sentences', nb=3)


class GenePanelSnapshotFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = GenePanelSnapshot

    level4title = factory.SubFactory(Level4TitleFactory)
    panel = factory.SubFactory('panels.tests.factories.GenePanelFactory', genepanelsnapshot=None)
    major_version = 0
    minor_version = 0
    old_panels = factory.Faker('sentences', nb=3)


class GenePanelFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = GenePanel

    name = factory.Faker('sentence')
    genepanelsnapshot = factory.RelatedFactory(GenePanelSnapshotFactory)


class GeneFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Gene

    gene_symbol = factory.LazyAttribute(lambda g: factory.Faker('md5').evaluate(0, 0, 0)[:7])
    other_transcripts = json.dumps({})


class EvidenceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Evidence

    name = factory.LazyAttribute(lambda n: Evidence.ALL_SOURCES[randint(0, 9)])
    rating = 5
    comment = ""
    reviewer = factory.SubFactory('accounts.tests.factories.ReviewerFactory')


class EvaluationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Evaluation
    user = factory.SubFactory('accounts.tests.factories.UserFactory')


class TrackRecordFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TrackRecord


class TagFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Tag

    name = factory.Faker('word')


class CommentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Comment


class GenePanelEntrySnapshotFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = GenePanelEntrySnapshot
        django_get_or_create = False

    panel = factory.SubFactory(GenePanelSnapshotFactory)
    gene_core = factory.SubFactory(GeneFactory)
    publications = factory.Faker('sentences', nb=3)
    phenotypes = factory.Faker('sentences', nb=3)
    moi = Evaluation.MODES_OF_INHERITANCE.Unknown
    mode_of_pathogenicity = Evaluation.MODES_OF_PATHOGENICITY['Other - please provide details in the comments']
    saved_gel_status = 0
    gene = factory.LazyAttribute(lambda g: g.gene_core.dict_tr())

    @factory.post_generation
    def evaluation(self, create, extracted, **kwargs):
        if not create:
            return

        evaluations = extracted
        if not extracted:
            evaluations = EvaluationFactory.create_batch(4)

        for evaluation in evaluations:
            self.evaluation.add(evaluation)

    @factory.post_generation
    def evidence(self, create, extracted, **kwargs):
        if not create:
            return

        evidences = extracted
        if not extracted:
            evidences = EvidenceFactory.create_batch(4)

        for evidence in evidences:
            self.evidence.add(evidence)
