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
from django.db import models
from django.contrib.postgres.fields import ArrayField
from model_utils.models import TimeStampedModel
from model_utils import Choices

from accounts.models import User
from .comment import Comment


class Evaluation(TimeStampedModel):
    """
    TODO @migrate ratings from old format into the new one?
    """

    class Meta:
        indexes = [models.Index(fields=["rating"])]
        ordering = ["-created"]

    RATINGS = Choices(
        ("GREEN", "Green List (high evidence)"),
        ("RED", "Red List (low evidence)"),
        ("AMBER", "I don't know"),
    )

    MODES_OF_INHERITANCE = Choices(
        ("", "Provide a mode of inheritance"),
        (
            "MONOALLELIC, autosomal or pseudoautosomal, NOT imprinted",
            "MONOALLELIC, autosomal or pseudoautosomal, NOT imprinted",
        ),  # noqa
        (
            "MONOALLELIC, autosomal or pseudoautosomal, maternally imprinted (paternal allele expressed)",
            "MONOALLELIC, autosomal or pseudoautosomal, maternally imprinted (paternal allele expressed)",
        ),  # noqa
        (
            "MONOALLELIC, autosomal or pseudoautosomal, paternally imprinted (maternal allele expressed)",
            "MONOALLELIC, autosomal or pseudoautosomal, paternally imprinted (maternal allele expressed)",
        ),  # noqa
        (
            "MONOALLELIC, autosomal or pseudoautosomal, imprinted status unknown",
            "MONOALLELIC, autosomal or pseudoautosomal, imprinted status unknown",
        ),  # noqa
        (
            "BIALLELIC, autosomal or pseudoautosomal",
            "BIALLELIC, autosomal or pseudoautosomal",
        ),
        (
            "BOTH monoallelic and biallelic, autosomal or pseudoautosomal",
            "BOTH monoallelic and biallelic, autosomal or pseudoautosomal",
        ),  # noqa
        (
            "BOTH monoallelic and biallelic (but BIALLELIC mutations cause a more SEVERE disease form), autosomal or pseudoautosomal",
            "BOTH monoallelic and biallelic (but BIALLELIC mutations cause a more SEVERE disease form), autosomal or pseudoautosomal",
        ),  # noqa
        (
            "X-LINKED: hemizygous mutation in males, biallelic mutations in females",
            "X-LINKED: hemizygous mutation in males, biallelic mutations in females",
        ),  # noqa
        (
            "X-LINKED: hemizygous mutation in males, monoallelic mutations in females may cause disease (may be less severe, later onset than males)",
            "X-LINKED: hemizygous mutation in males, monoallelic mutations in females may cause disease (may be less severe, later onset than males)",
        ),  # noqa
        ("MITOCHONDRIAL", "MITOCHONDRIAL"),
        ("Unknown", "Unknown"),
        ("Other", "Other - please specifiy in evaluation comments"),
    )

    MODES_OF_PATHOGENICITY = Choices(
        ("", "Provide exceptions to loss-of-function"),
        (
            "Loss-of-function variants (as defined in pop up message) DO NOT cause this phenotype - please provide details in the comments",
            "Loss-of-function variants (as defined in pop up message) DO NOT cause this phenotype - please provide details in the comments",
        ),  # noqa
        ("Other", "Other - please provide details in the comments"),
    )

    user = models.ForeignKey(User, on_delete=models.PROTECT)
    rating = models.CharField(max_length=255, choices=RATINGS, blank=True)
    mode_of_pathogenicity = models.CharField(
        choices=MODES_OF_PATHOGENICITY, null=True, blank=True, max_length=255
    )
    publications = ArrayField(models.TextField(), blank=True, null=True)
    phenotypes = ArrayField(models.TextField(), blank=True, null=True)
    moi = models.CharField(
        "Mode of Inheritance",
        choices=MODES_OF_INHERITANCE,
        null=True,
        blank=True,
        max_length=255,
    )
    current_diagnostic = models.BooleanField(default=False, blank=True)
    clinically_relevant = models.NullBooleanField(
        default=False,
        blank=True,
        null=True,
        help_text="Interruptions in the repeated sequence are reported as part of standard diagnostic practise",
    )
    version = models.CharField(null=True, blank=True, max_length=255)
    comments = models.ManyToManyField(Comment)
    last_updated = models.DateTimeField(null=True, blank=True)

    @property
    def entity(self):
        if self.str_set.first():
            return self.str_set.first()
        elif self.region_set.first():
            return self.region_set.first()
        elif self.genepanelentrysnapshot_set.first():
            return self.genepanelentrysnapshot_set.first()

    def __str__(self):
        entity = self.entity
        return "{} review by {}".format(entity.label, self.user.get_full_name())

    def is_comment_without_review(self):
        if (
            self.rating
            or self.comments.count == 0
            or self.moi
            or self.mode_of_pathogenicity
            or self.current_diagnostic
            or self.clinically_relevant
            or self.publications
            or self.phenotypes
        ):
            return False
        return True

    def dict_tr(self):
        return {
            "user": self.user,
            "rating": self.rating,
            "moi": self.moi,
            "comments": [c.dict_tr() for c in self.comments.all()],
            "mode_of_pathogenicity": self.mode_of_pathogenicity,
            "phenotypes": self.phenotypes,
            "publications": self.publications,
            "current_diagnostic": self.current_diagnostic,
            "clinically_relevant": self.clinically_relevant,
            "version": self.version,
            "date": self.created,
        }
