from django import forms
from .gene import UpdateGeneTagsForm
from .gene import UpdateGeneMOPForm
from .gene import UpdateGeneMOIForm
from .gene import UpdateGenePhenotypesForm
from .gene import UpdateGenePublicationsForm
from .gene import UpdateGeneRatingForm
from .gene import UpdateGeneTagsForm
from .strs import UpdateSTRTagsForm
from .strs import UpdateSTRMOIForm
from .strs import UpdateSTRPhenotypesForm
from .strs import UpdateSTRPublicationsForm
from .strs import UpdateSTRRatingForm
from .region import UpdateRegionTagsForm
from .region import UpdateRegionMOIForm
from .region import UpdateRegionPhenotypesForm
from .region import UpdateRegionPublicationsForm
from .region import UpdateRegionRatingForm


class EditCommentForm(forms.Form):
    comment = forms.CharField(widget=forms.Textarea)
