from django import forms


class Select2ListMultipleChoiceField(forms.MultipleChoiceField):
    def __init__(self, choice_list=None, required=True, widget=None,
                 label=None, initial=None, help_text='', *args, **kwargs):
        choice_list = choice_list or []
        if callable(choice_list):
            choices = [(choice, choice) for choice in choice_list()]
        else:
            choices = [(choice, choice) for choice in choice_list]

        super(Select2ListMultipleChoiceField, self).__init__(
            choices=choices, required=required, widget=widget, label=label,
            initial=initial, help_text=help_text, *args, **kwargs
        )
