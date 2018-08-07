from collections import OrderedDict
from django import forms
from dal_select2.widgets import ModelSelect2Multiple
from panels.models import Level4Title
from panels.models import GenePanel
from panels.models import GenePanelSnapshot
from panels.models import PanelType


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

    types = forms.ModelMultipleChoiceField(
        label="Panel Types",
        required=False,
        queryset=PanelType.objects.all(),
        widget=ModelSelect2Multiple(
            url="autocomplete-simple-panel-types",
            attrs={'data-minimum-input-length': 1}
        )
    )

    class Meta:
        model = GenePanelSnapshot
        fields = ('old_panels', )

    def __init__(self, *args, **kwargs):
        gel_curator = kwargs.pop('gel_curator')
        self.request = kwargs.pop('request')

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
        self.fields['types'] = original_fields.get('types')
        if gel_curator:  # TODO (Oleg) also check if we have entities in this panel
            self.fields['child_panels'] = original_fields.get('child_panels')
        self.fields['status'] = original_fields.get('status')

        if self.instance.pk:
            self.fields['status'].initial = self.instance.panel.status
            if gel_curator:
                self.fields['child_panels'].initial = self.instance.child_panels.values_list('pk', flat=True)
                self.fields['types'].initial = self.instance.panel.types.values_list('pk', flat=True)

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

        activities = []

        if self.instance.id:
            panel = self.instance.panel
            level4title = self.instance.level4title

            data_changed = False
            if level4title.dict_tr() != new_level4.dict_tr():
                data_changed = True
                new_level4.save()
                activities.append("Panel name changed from {} to {}".format(
                    level4title.name,
                    new_level4.name
                ))
                self.instance.level4title = new_level4
                self.instance.panel.name = new_level4.name

            if 'old_panels' in self.changed_data:
                activities.append("List of old panels changed from {} to {}".format(
                    "; ".join(self.instance.old_panels),
                    "; ".join(self.cleaned_data['old_panels'])
                ))
                self.instance.old_panels = self.cleaned_data['old_panels']
            
            if 'status' in self.changed_data:
                activities.append("Panel status changed from {} to {}".format(
                    self.instance.panel.status,
                    self.cleaned_data['status']
                ))
                self.instance.panel.status = self.cleaned_data['status']

            if 'child_panels' in self.changed_data:
                self.instance.child_panels.set(self.cleaned_data['child_panels'])
                activities.append("Changed child panels to: {}".format(
                    self.instance.child_panels.values_list('panel__name', flat=True)
                ))

            if 'types' in self.cleaned_data:
                activities.append("Panel types changed from {} to {}".format(
                    "; ".join(panel.types.values_list('name', flat=True)),
                    "; ".join(self.cleaned_data['types'])
                ))
                panel.types.set(self.cleaned_data['types'])

            if data_changed or self.changed_data:
                self.instance.increment_version()
                panel.save()
                self.instance.update_saved_stats()
            else:
                panel.save()

        else:
            panel = GenePanel.objects.create(
                name=self.cleaned_data['level4'].strip(),
                status=self.cleaned_data['status']
            )
            new_level4.save()

            activities.append("Added Panel {}".format(panel.name))
            if self.cleaned_data['old_panels']:
                activities.append("Set list of old panels to {}".format(
                    "; ".join(self.cleaned_data['old_panels'])))

            self.instance.panel = panel
            self.instance.level4title = new_level4
            self.instance.old_panels = self.cleaned_data['old_panels']
            self.instance.save()
            if self.cleaned_data.get('child_panels'):
                self.instance.child_panels.set(self.cleaned_data['child_panels'])
                self.instance.major_version = max(self.instance.child_panels.values_list('major_version', flat=True))
                self.instance.save(update_fields=['major_version', ])
                self.instance.update_saved_stats()
                activities.append("Set child panels to: {}".format(
                    self.instance.child_panels.values_list('panel__name', flat=True)
                ))
            if self.cleaned_data.get('types'):
                panel.types.set(self.cleaned_data['types'])
                activities.append("Set panel types to: {}".format(
                    panel.types.values_list('name', flat=True)
                ))

        panel.add_activity(self.request.user, "\n".join(activities))

    @staticmethod
    def _clean_array(data, separator=","):
        return [x.strip() for x in data.split(separator) if x.strip()]
