from django.db import models


class GenePanelEntry(models.Model):
    panel = models.OneToOneField(GenePanel)
    gene = EmbeddedModelField(Gene)
    evidence = ListField(EmbeddedModelField(Evidence))
    evaluation = ListField(EmbeddedModelField(Evaluation))
    moi = models.CharField(max_length=255)
    penetrance = models.CharField(max_length=255)
    track = ListField(EmbeddedModelField(TrackRecord))
    publications = ListField(models.CharField())
    phenotypes = ListField(models.CharField())
    tags = ListField(models.CharField(max_length=30)) # will be one to one
    flagged = BooleanField()
    ready = models.NullBooleanField(default=False)
    curator_comments = ListField(EmbeddedModelField(CuratorComment)) # ? is it for the panel itself, or this version or both?
    contributors = ListField(models.CharField(max_length=255))
    mode_of_pathogenicity = models.CharField(max_length=255)
