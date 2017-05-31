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

    RATINGS = Choices(
        ("GREEN", "Green List (high evidence)"),
        ("RED", "Red List (low evidence)"),
        ("AMBER", "I don't know")
    )

    MODES_OF_INHERITANCE = Choices(
        ("", "Provide a mode of inheritance"),
        ("MONOALLELIC, autosomal or pseudoautosomal, NOT imprinted", "MONOALLELIC, autosomal or pseudoautosomal, NOT imprinted"),
        ("MONOALLELIC, autosomal or pseudoautosomal, maternally imprinted (paternal allele expressed)", "MONOALLELIC, autosomal or pseudoautosomal, maternally imprinted (paternal allele expressed)"),
        ("MONOALLELIC, autosomal or pseudoautosomal, paternally imprinted (maternal allele expressed)", "MONOALLELIC, autosomal or pseudoautosomal, paternally imprinted (maternal allele expressed)"),
        ("MONOALLELIC, autosomal or pseudoautosomal, imprinted status unknown", "MONOALLELIC, autosomal or pseudoautosomal, imprinted status unknown"),
        ("BIALLELIC, autosomal or pseudoautosomal", "BIALLELIC, autosomal or pseudoautosomal"),
        ("BOTH monoallelic and biallelic, autosomal or pseudoautosomal", "BOTH monoallelic and biallelic, autosomal or pseudoautosomal"),
        ("BOTH monoallelic and biallelic (but BIALLELIC mutations cause a more SEVERE disease form), autosomal or pseudoautosomal", "BOTH monoallelic and biallelic (but BIALLELIC mutations cause a more SEVERE disease form), autosomal or pseudoautosomal"),
        ("X-LINKED: hemizygous mutation in males, biallelic mutations in females", "X-LINKED: hemizygous mutation in males, biallelic mutations in females"),
        ("X-LINKED: hemizygous mutation in males, monoallelic mutations in females may cause disease (may be less severe, later onset than males)", "X-LINKED: hemizygous mutation in males, monoallelic mutations in females may cause disease (may be less severe, later onset than males)"),
        ("MITOCHONDRIAL", "MITOCHONDRIAL"),
        ("Unknown", "Unknown"),
        ("Other - please specifiy in evaluation comments", "Other - please specifiy in evaluation comments"),
    )

    MODES_OF_PHATHOGENICITY = Choices(
        ("", "Provide exceptions to loss-of-function"),
        ("Loss-of-function variants (as defined in pop up message) DO NOT cause this phenotype - please provide details in the comments", "Loss-of-function variants (as defined in pop up message) DO NOT cause this phenotype - please provide details in the comments"),
        ("Other - please provide details in the comments", "Other - please provide details in the comments"),
    )

    user = models.ForeignKey(User)
    rating = models.CharField(max_length=255, choices=RATINGS)
    transcript = models.CharField(null=True,  blank=True, max_length=255)
    mode_of_pathogenicity = models.CharField(choices=MODES_OF_PHATHOGENICITY, null=True,  blank=True, max_length=255)
    publications = ArrayField(models.CharField(null=True,  blank=True, max_length=255))
    phenotypes = ArrayField(models.CharField(null=True,  blank=True, max_length=255))
    moi = models.CharField("Mode of Inheritance", choices=MODES_OF_INHERITANCE, null=True,  blank=True, max_length=255)
    current_diagnostic = models.BooleanField(default=False)
    version = models.CharField(null=True, blank=True, max_length=255)
    comments = models.ManyToManyField(Comment)

    def dict_tr(self):
        return {
            "user": self.user,
            "rating": self.rating,
            "transcript": self.transcript,
            "moi": self.moi,
            "comments": [c.dict_tr() for c in self.comments.all()],
            "mode_of_pathogenicity": self.mode_of_pathogenicity,
            "phenotypes": self.phenotypes,
            "publications": self.publications,
            "current_diagnostic": self.current_diagnostic,
            "version": self.version,
            "date": self.created
        }
