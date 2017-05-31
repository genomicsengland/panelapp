from django.contrib import admin

from .models import GenePanel
from .models import GenePanelSnapshot
from .models import GenePanelEntrySnapshot


admin.site.register(GenePanel)
admin.site.register(GenePanelSnapshot)
admin.site.register(GenePanelEntrySnapshot)
