##
## Copyright (c) 2016-2019 Genomics England Ltd.
##
## This file is part of PanelApp
## (see https://panelapp.genomicsengland.co.uk).
##
## Licensed to the Apache Software Foundation (ASF) under one
## or more contributor license agreements.  See the NOTICE file
## distributed with this work for additional information
## regarding copyright ownership.  The ASF licenses this file
## to you under the Apache License, Version 2.0 (the
## "License"); you may not use this file except in compliance
## with the License.  You may obtain a copy of the License at
##
##   http://www.apache.org/licenses/LICENSE-2.0
##
## Unless required by applicable law or agreed to in writing,
## software distributed under the License is distributed on an
## "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
## KIND, either express or implied.  See the License for the
## specific language governing permissions and limitations
## under the License.
##
import factory
from uuid import uuid1
from random import randint
from random import choice
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
from panels.models import STR
from panels.models import Region
from panels.models import PanelType
from psycopg2.extras import NumericRange

from faker import Faker

fake = Faker()


class Level4TitleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Level4Title

    name = factory.LazyAttribute(
        lambda x: fake.sentence(nb_words=6, variable_nb_words=True).strip(".")
    )
    description = factory.Faker("sentence", nb_words=6, variable_nb_words=True)
    level3title = factory.Faker("sentence", nb_words=6, variable_nb_words=True)
    level2title = factory.Faker("sentence", nb_words=6, variable_nb_words=True)
    omim = factory.Faker("sentences", nb=3)
    orphanet = factory.Faker("sentences", nb=3)
    hpo = factory.Faker("sentences", nb=3)


class GenePanelSnapshotFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = GenePanelSnapshot

    level4title = factory.SubFactory(Level4TitleFactory)
    panel = factory.SubFactory(
        "panels.tests.factories.GenePanelFactory", genepanelsnapshot=None
    )
    major_version = 0
    minor_version = 0
    old_panels = factory.Faker("sentences", nb=3)

    @factory.post_generation
    def stats(self, create, stats, **kwargs):
        if not create:
            return

        self._update_saved_stats()


class GenePanelFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = GenePanel

    name = factory.LazyAttribute(
        lambda x: fake.sentence(nb_words=6, variable_nb_words=True).strip(".")
    )
    genepanelsnapshot = factory.RelatedFactory(GenePanelSnapshotFactory)
    old_pk = '553f9696bb5a1616e5ed41e3'


class PanelTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PanelType

    name = factory.Faker("word")
    description = factory.Faker("sentences", nb=3)


class GeneFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Gene

    gene_symbol = factory.LazyAttribute(
        lambda g: factory.Faker("md5").evaluate(0, 0, 0)[:7]
    )
    ensembl_genes = {}


class EvidenceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Evidence

    name = factory.LazyAttribute(lambda n: Evidence.ALL_SOURCES[randint(0, 9)])
    rating = 5
    comment = ""
    reviewer = factory.SubFactory("accounts.tests.factories.ReviewerFactory")


class EvaluationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Evaluation

    user = factory.SubFactory("accounts.tests.factories.UserFactory")


class TrackRecordFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TrackRecord

    user = factory.SubFactory("accounts.tests.factories.UserFactory")


class TagFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Tag

    name = factory.LazyAttribute(lambda o: uuid1().hex)


class CommentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Comment


class GenePanelEntrySnapshotFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = GenePanelEntrySnapshot
        django_get_or_create = False

    panel = factory.SubFactory(GenePanelSnapshotFactory)
    gene_core = factory.SubFactory(GeneFactory)
    publications = factory.Faker("sentences", nb=3)
    phenotypes = factory.Faker("sentences", nb=3)
    moi = Evaluation.MODES_OF_INHERITANCE.Unknown
    mode_of_pathogenicity = Evaluation.MODES_OF_PATHOGENICITY.Other
    saved_gel_status = 0
    gene = factory.LazyAttribute(lambda g: g.gene_core.dict_tr())

    @factory.post_generation
    def evaluation(self, create, evaluations, **kwargs):
        if not create:
            return

        if not evaluations:
            evaluations = EvaluationFactory.create_batch(4)

        for evaluation in evaluations:
            if evaluation:
                self.evaluation.add(evaluation)

    @factory.post_generation
    def evidence(self, create, extracted, **kwargs):
        if not create:
            return

        evidences = extracted
        if not extracted:
            evidences = EvidenceFactory.create_batch(4)

        for evidence in evidences:
            if evidence:
                self.evidence.add(evidence)

    @factory.post_generation
    def tags(self, create, tags, **kwargs):
        if not create:
            return

        if not tags:
            tags = TagFactory.create_batch(1)

        for tag in tags:
            if tag:
                self.tags.add(tag)

    @factory.post_generation
    def stats(self, create, stats, **kwargs):
        if not create:
            return

        self.panel._update_saved_stats()


class FakeRange:
    def __init__(self):
        self.lower = randint(1, 10)
        self.upper = randint(11, 20)


class STRFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = STR
        django_get_or_create = False

    name = factory.Faker("word")
    chromosome = factory.LazyAttribute(lambda s: choice(STR.CHROMOSOMES)[0])
    position_37 = factory.LazyAttribute(
        lambda s: NumericRange(randint(1, 10), randint(11, 20))
    )
    position_38 = factory.LazyAttribute(
        lambda s: NumericRange(randint(1, 10), randint(11, 20))
    )
    repeated_sequence = factory.Faker("word")
    normal_repeats = factory.LazyAttribute(lambda s: randint(1, 10))
    pathogenic_repeats = factory.LazyAttribute(lambda s: randint(11, 20))
    panel = factory.SubFactory(GenePanelSnapshotFactory)
    gene_core = factory.SubFactory(GeneFactory)
    publications = factory.Faker("sentences", nb=3)
    phenotypes = factory.Faker("sentences", nb=3)
    moi = Evaluation.MODES_OF_INHERITANCE.Unknown
    saved_gel_status = 0
    gene = factory.LazyAttribute(lambda g: g.gene_core.dict_tr())

    @factory.post_generation
    def evaluation(self, create, evaluations, **kwargs):
        if not create:
            return

        if not evaluations:
            evaluations = EvaluationFactory.create_batch(4)

        for evaluation in evaluations:
            if evaluation:
                self.evaluation.add(evaluation)

    @factory.post_generation
    def tags(self, create, tags, **kwargs):
        if not create:
            return

        if not tags:
            tags = TagFactory.create_batch(1)

        for tag in tags:
            if tag:
                self.tags.add(tag)

    @factory.post_generation
    def evidence(self, create, extracted, **kwargs):
        if not create:
            return

        evidences = extracted
        if not extracted:
            evidences = EvidenceFactory.create_batch(4)

        for evidence in evidences:
            if evidence:
                self.evidence.add(evidence)

    @factory.post_generation
    def stats(self, create, stats, **kwargs):
        if not create:
            return

        self.panel._update_saved_stats()


class RegionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Region
        django_get_or_create = False

    name = factory.Faker("word")
    verbose_name = factory.Faker("word")
    chromosome = factory.LazyAttribute(lambda s: choice(STR.CHROMOSOMES)[0])
    position_37 = factory.LazyAttribute(
        lambda s: NumericRange(randint(1, 10), randint(11, 20))
    )
    position_38 = factory.LazyAttribute(
        lambda s: NumericRange(randint(1, 10), randint(11, 20))
    )
    haploinsufficiency_score = factory.LazyAttribute(
        lambda s: choice(Region.DOSAGE_SENSITIVITY_SCORES)[0]
    )
    triplosensitivity_score = factory.LazyAttribute(
        lambda s: choice(Region.DOSAGE_SENSITIVITY_SCORES)[0]
    )
    type_of_variants = Region.VARIANT_TYPES.cnv_gain
    required_overlap_percentage = factory.LazyAttribute(lambda s: randint(0, 100))
    panel = factory.SubFactory(GenePanelSnapshotFactory)
    gene_core = factory.SubFactory(GeneFactory)
    publications = factory.Faker("sentences", nb=3)
    phenotypes = factory.Faker("sentences", nb=3)
    moi = Evaluation.MODES_OF_INHERITANCE.Unknown
    saved_gel_status = 0
    gene = factory.LazyAttribute(lambda g: g.gene_core.dict_tr())

    @factory.post_generation
    def evaluation(self, create, evaluations, **kwargs):
        if not create:
            return

        if not evaluations:
            evaluations = EvaluationFactory.create_batch(4)

        for evaluation in evaluations:
            if evaluation:
                self.evaluation.add(evaluation)

    @factory.post_generation
    def evidence(self, create, extracted, **kwargs):
        if not create:
            return

        evidences = extracted
        if not extracted:
            evidences = EvidenceFactory.create_batch(4)

        for evidence in evidences:
            if evidence:
                self.evidence.add(evidence)

    @factory.post_generation
    def stats(self, create, stats, **kwargs):
        if not create:
            return

        self.panel._update_saved_stats()
