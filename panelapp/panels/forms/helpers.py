from django.utils.translation import gettext_lazy as _
from django.contrib.postgres.forms import SimpleArrayField


class GELSimpleArrayField(SimpleArrayField):
    default_error_messages = {
        'item_invalid': _('Make sure there is no ; if no value after: %(nth)s item: '),
    }
