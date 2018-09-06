from django import forms


class ActivityFilterForm(forms.Form):
    panel = forms.ChoiceField(required=False, choices=list)
    version = forms.ChoiceField(required=False, choices=list)
    entity = forms.ChoiceField(label="Gene or Genomic Entity Name", required=False, choices=list)
    date_from = forms.DateField(required=False,
                                widget=forms.DateInput(attrs={
                                    'type': 'date',
                                    'placeholder': 'Date in YYYY-MM-DD format',
                                    'pattern': '[0-9]{4}-[0-9]{2}-[0-9]{2}'
                                }))
    date_to = forms.DateField(required=False,
                              widget=forms.DateInput(attrs={
                                  'type': 'date',
                                  'placeholder': 'Date in YYYY-MM-DD format',
                                  'pattern': '[0-9]{4}-[0-9]{2}-[0-9]{2}'
                              }))

    def __init__(self, *args, **kwargs):
        panels = kwargs.pop('panels')
        versions = kwargs.pop('versions')
        entities = kwargs.pop('entities')

        super().__init__(*args, **kwargs)

        self.fields['panel'].choices = [('', 'Panel')] + list(panels)

        if versions:
            self.fields['version'].choices = [('', 'Panel Version')] + list(versions)
        else:
            self.fields['version'].widget.attrs = {'disabled': 'disabled'}

        if entities:
            self.fields['entity'].choices = [('', '')] + list(entities)
        else:
            self.fields['entity'].widget.attrs = {'disabled': 'disabled'}
