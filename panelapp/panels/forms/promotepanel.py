from django import forms
from panels.models import GenePanelSnapshot


class PromotePanelForm(forms.ModelForm):
    """
    This form increments a major version and saves new version comment
    """
    version_comment = forms.CharField(label="Comment about this new version", widget=forms.Textarea)

    class Meta:
        model = GenePanelSnapshot
        fields = ('version_comment',)

    def save(self, *args, commit=True, **kwargs):
        self.instance.increment_version(major=True)
        return self.instance
