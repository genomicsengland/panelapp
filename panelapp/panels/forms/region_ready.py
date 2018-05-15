from django import forms
from panels.models import Region


class RegionReadyForm(forms.ModelForm):
    """
    This class marks Gene as Ready and also adds a comment if it was provided.
    It also saves a new evidence with the current Gene status as an evidence.
    Additionally, we add save a TrackRecord to note this change, and record an activity
    """

    ready_comment = forms.CharField(
        label="Comment (eg What decisions are being made?)",
        required=False,
        widget=forms.Textarea
    )

    class Meta:
        model = Region
        fields = ('comments',)

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request')
        super().__init__(*args, **kwargs)

        original_fields = self.fields
        self.fields = {}
        self.fields['ready_comment'] = original_fields.get('ready_comment')

    def save(self, *args, **kwargs):
        self.instance.mark_as_ready(self.request.user, self.cleaned_data['ready_comment'])
