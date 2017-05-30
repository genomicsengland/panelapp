"""
# Panel app data structure

Brief overview of how the data in this app is structured.

## How panel app data should be structured

We have genes - they don’t change, can only be imported by the GEL reviewers.
We also have panels - which holds basic information about the pane.
Panel is the list of Genes, but Genes that are specific to this Panel, i.e. they
can be slightly different from the Genes imported via Import tool.

When adding a panel a curator provides the basic info for this panel.

Reviewers can add a Gene to the panel, this is autocompleted in the form from
the existing Genes.

Reviewers can add comments, new information.

Each time something changes in the panel we create a copy of the panel and copy
the gene panel entry, meaning we have version for each gene panel. This
information can be retrieved from the API and also can be downloaded via tsv.

However, the only version which is visible is the latest version of the gene
panel entry.

Previusly the application was using MongoDB, thus it was easy to create an
embedded version for the previous versions in the list. Since we are moving
to the Postgres it makes sense to keep the gene panel entry backup as a JSON.

## V2 suggestions

GenePanel is mainly a placeholder that contains mainly the panel status
(approved or not), other flags and everything else computed on the or via
SQL queries.

Since we want to keep a log of how the panel evolved we'd need to keep the version
as a snapshot, meaning that Gene, Transcript, Level4Title, GenePanel, Evidence,
Comments, Evaluation, TrackRecord are never deleted, they are kept for the reference
in Snapshot models.

Snapshot models have many to many most of these supporting models, and each
snapshot might have (usually) more values added to it.

For example, when we create a new evidence for the GenePanelEntry, we create a new
snapshot, that snapshot is the active GenePanelEntry and we add a new evidence.
If we want to remove an evidence from the GenePanelEntry we create a new version
of GenePanelEntry and remove ManyToMany record from the new GenePanelEntry.

# done
class Gene(models.Model):
    gene_symbol = models.CharField(max_length=255, primary_key=True)
    gene_name = models.CharField(max_length=255)
    other_transcripts = JSONField()
    omim_gene = models.CharField(max_length=255)
    # variants = ListField(EmbeddedModelField(Variant)) # removed

# done
REMOVED

I will remove this model and use JSONField on Gene.other_transcripts field instead
Looks like we only use this data when we export the information via tsv or webservices
I don't see a way to add new other transcripts on the website Frontend, only via
import Gene tool

Is this unique per Gene or Multiple genes can use the same transcript?
I.e. do we create a new transcript each time we import genes, or we try to
find the transcript via geneid or any other attributes of this class

class Transcript(models.Model):

    name = models.CharField(max_length=255)
    geneid = models.CharField(max_length=255)
    TSL = models.CharField(max_length=255)
    genecode = models.CharField(max_length=255)
    APPRIS = models.CharField(max_length=255)
    refseq = models.CharField(max_length=255)
    CDSid = models.CharField(max_length=255)
    biotype = models.CharField(max_length=255)
    uniprot = models.CharField(max_length=255)
    transcriptLength = models.IntegerField()

####

# done
class Level4Title(models.Model): # foreign key or use as panel
    name = models.CharField(max_length=255)
    description = models.TextField()
    level3title = models.CharField(max_length=255)
    level2title = models.CharField(max_length=255)
    omim = ArrayField(models.CharField(max_length=255))
    orphanet = ArrayField(models.CharField(max_length=255))
    hpo = ArrayField(models.CharField(max_length=255))

# done
class GenePanel(models.Model):
    level4title = models.ForeignKey(Level4Title)
    approved = models.BooleanField(default=False)
    promoted = models.BooleanField(default=False)
    old_panels = ArrayField(models.CharField(max_length=255))

# done
class Evidence(models.Model):
    name = models.CharField(max_length=255)  # name of the user?
    rating = models.IntegerField()
    comment = models.CharField(max_length=255)
    date = models.DateTimeField()
    type = models.CharField(max_length=255)

# done
class Comment(models.Model):
    date = models.DateTimeField()
    comment = models.TextField()
    user = models.ForeignKey(User)

# done
class Evaluation(models.Model):
    user = models.ForeignKey(User)
    rating = models.CharField(max_length=255)
    transcript = models.CharField(null=True,  blank=True, max_length=255)
    mode_of_pathogenicity = models.CharField(null=True,  blank=True, max_length=255)
    publications = ArrayField(models.CharField(null=True,  blank=True, max_length=255))
    phenotypes = ArrayField(models.CharField(null=True,  blank=True, max_length=255))
    moi = models.CharField(null=True,  blank=True, max_length=255)
    current_diagnostic = models.BooleanField(default=False)
    version = models.CharField(null=True, blank=True, max_length=255)
    date = models.DateTimeField(null=True)
    comments = models.ManyToMany(Comment)

# done
class Activity(models.Model):
    panel_id = models.CharField(max_length=255)
    gene_symbol = models.CharField(max_length=255)
    user = models.CharField(max_length=255)
    text = models.CharField(max_length=255)
    date = models.DateTimeField()

# done
This needs to be refactored. How TrackRecords are different to Activities?
class TrackRecord(models.Model):
    date = models.DateTimeField()
    issue_type = models.CharField(max_length=255)
    issue_description = models.CharField(max_length=255)
    user = models.CharField(max_length=255)
    gel_status = models.IntegerField()
    curator_status = models.IntegerField()

# done
class GenePanelSnapshot(models.Model):
    panel = models.ForeignKey(GenePanel)
    major_version = models.IntegerField()
    minor_version = models.IntegerField()
    version_comment = models.TextField()

# done
class GenePanelEntrySnapshot(models.Model):
    panel = models.ForeignKey(GenePanelSnapshot)
    gene = JSONField() # copy data from Gene.dict_tr
    gene_core = models.ForeignKey(Gene)  # reference to the original Gene
    evidence = models.ManyToMany(Evidence)
    evaluation = models.ManyToMany(Evaluation)
    moi = models.CharField(max_length=255)
    penetrance = models.CharField(max_length=255)
    track = models.ManyToMany(TrackRecord)
    publications = ArrayField(models.CharField())
    phenotypes = ArrayField(models.CharField())
    tags = ArrayField(models.CharField(max_length=30))
    flagged = models.BooleanField()
    ready = models.BooleanField(default=False)
    comments = models.ManyToMany(Comment)
    contributors = models.ManyToMany(User)
    mode_of_pathogenicity = models.CharField(max_length=255)

"""

from .gene import Gene  # noqa
from .activity import Activity  # noqa
from .level4title import Level4Title  # noqa
from .comment import Comment  # noqa
from .evaluation import Evaluation  # noqa
from .evidence import Evidence  # noqa
from .trackrecord import TrackRecord  # noqa
from .genepanel import GenePanel  # noqa
from .genepanelsnapshot import GenePanelSnapshot  # noqa
from .genepanelentrysnapshot import GenePanelEntrySnapshot  # noqa
from .import_tools import UploadedGeneList  # noqa
from .import_tools import UploadedPanelList  # noqa
from .import_tools import UploadedReviewsList  # noqa
