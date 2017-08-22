from collections import OrderedDict
from django import forms
from panels.models import Level4Title
from panels.models import GenePanel
from panels.models import GenePanelSnapshot


class PanelForm(forms.ModelForm):
    level2 = forms.CharField(required=False)
    level3 = forms.CharField(required=False)
    level4 = forms.CharField()
    description = forms.CharField(widget=forms.Textarea)
    omim = forms.CharField(required=False)
    orphanet = forms.CharField(required=False)
    hpo = forms.CharField(required=False)

    class Meta:
        model = GenePanelSnapshot
        fields = ('old_panels',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        original_fields = self.fields

        self.fields = OrderedDict()
        self.fields['level2'] = original_fields.get('level2')
        self.fields['level3'] = original_fields.get('level3')
        self.fields['level4'] = original_fields.get('level4')
        self.fields['description'] = original_fields.get('description')
        self.fields['omim'] = original_fields.get('omim')
        self.fields['orphanet'] = original_fields.get('orphanet')
        self.fields['hpo'] = original_fields.get('hpo')
        self.fields['old_panels'] = original_fields.get('old_panels')

    def clean_omim(self):
        return self._clean_array(self.cleaned_data['omim'])

    def clean_orphanet(self):
        return self._clean_array(self.cleaned_data['orphanet'])

    def clean_hpo(self):
        return self._clean_array(self.cleaned_data['hpo'])

    def save(self, *args, **kwargs):
        new_level4 = Level4Title(
            level2title=self.cleaned_data['level2'].strip(),
            level3title=self.cleaned_data['level3'].strip(),
            name=self.cleaned_data['level4'].strip(),
            description=self.cleaned_data['description'].strip(),
            omim=self.cleaned_data['omim'],
            hpo=self.cleaned_data['hpo'],
            orphanet=self.cleaned_data['orphanet']
        )

        if self.instance.id:
            panel = self.instance.panel
            level4title = self.instance.level4title

            data_changed = False
            if level4title.dict_tr() != new_level4.dict_tr():
                data_changed = True
                new_level4.save()
                self.instance.level4title = new_level4
                self.instance.panel.name = new_level4.name

            if 'old_panels' in self.changed_data:
                data_changed = True
                self.instance.old_panels = self.cleaned_data['old_panels']

            if data_changed:
                self.instance.increment_version()
                self.instance.panel.save()

        else:
            panel = GenePanel.objects.create(name=self.cleaned_data['level4'].strip())
            new_level4.save()

            self.instance.panel = panel
            self.instance.level4title = new_level4
            self.instance.old_panels = self.cleaned_data['old_panels']
            self.instance.save()

    def _clean_array(self, data, separator=","):
        return [x.strip() for x in data.split(separator) if x.strip()]
