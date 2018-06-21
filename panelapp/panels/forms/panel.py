from collections import OrderedDict
from django import forms
from dal_select2.widgets import ModelSelect2Multiple
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
    status = forms.ChoiceField(required=True, choices=GenePanel.STATUS, initial=GenePanel.STATUS.internal)

    child_panels = forms.ModelMultipleChoiceField(
        label="Child Panels",
        required=False,
        queryset=GenePanelSnapshot.objects.get_active_annotated().exclude(is_super_panel=True),
        widget=ModelSelect2Multiple(
            url="autocomplete-simple-panels",
            attrs={'data-minimum-input-length': 3}
        )
    )

    class Meta:
        model = GenePanelSnapshot
        fields = ('old_panels',)

    def __init__(self, *args, **kwargs):
        gel_curator = kwargs.pop('gel_curator')

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
        if gel_curator:  # TODO (Oleg) also check if we have entities in this panel
            self.fields['child_panels'] = original_fields.get('child_panels')
        self.fields['status'] = original_fields.get('status')

        if self.instance.pk:
            self.fields['status'].initial = self.instance.panel.status
            if gel_curator:
                self.fields['child_panels'].initial = self.instance.child_panels.values_list('pk', flat=True)

    def clean_level4(self):
        if not self.instance.pk or self.cleaned_data['level4'] != self.instance.level4title.name:
            if GenePanelSnapshot.objects.get_active(all=True, internal=True).exclude(panel__status=GenePanel.STATUS.deleted).filter(
                    level4title__name=self.cleaned_data['level4']).exists():
                raise forms.ValidationError('Panel with this name already exists')

        return self.cleaned_data['level4']

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
                self.instance.old_panels = self.cleaned_data['old_panels']
            
            if 'status' in self.changed_data:
                self.instance.panel.status = self.cleaned_data['status']

            if 'child_panels' in self.changed_data:
                self.instance.child_panels.set(self.cleaned_data['child_panels'])

            if data_changed or self.changed_data:
                self.instance.increment_version()
                self.instance.panel.save()
                self.instance.update_saved_stats()
            else:
                self.instance.panel.save()

        else:
            panel = GenePanel.objects.create(
                name=self.cleaned_data['level4'].strip(),
                status=self.cleaned_data['status']
            )
            new_level4.save()

            self.instance.panel = panel
            self.instance.level4title = new_level4
            self.instance.old_panels = self.cleaned_data['old_panels']
            self.instance.save()
            if 'child_panels' in self.cleaned_data['child_panels']:
                self.instance.child_panels.set(self.cleaned_data['child_panels'])

    def _clean_array(self, data, separator=","):
        return [x.strip() for x in data.split(separator) if x.strip()]
