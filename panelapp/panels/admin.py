from django.contrib import admin

from .models import Tag
from .models import Gene
from .models import Activity
from .models import Level4Title
from .models import Comment
from .models import Evidence
from .models import Evaluation
from .models import TrackRecord
from .models import GenePanel
from .models import GenePanelSnapshot
from .models import GenePanelEntrySnapshot
from .models import UploadedGeneList
from .models import UploadedPanelList
from .models import UploadedReviewsList


class TagAdmin(admin.ModelAdmin):
    list_display = ('name',)


class GeneAdmin(admin.ModelAdmin):
    list_display = ('gene_symbol', 'gene_name', 'omim_gene',)
    search_fields = ('gene_symbol', 'gene_name',)


class ActivityAdmin(admin.ModelAdmin):
    list_display = ('created', 'gene_symbol', 'user',)
    search_fields = ('panel__name', 'gene_symbol',)


class Level4TitleAdmin(admin.ModelAdmin):
    list_display = ('name', 'level3title', 'level2title',)
    search_fields = (
        'name', 'level3title', 'level2title',
        'description', 'omim', 'orphanet', 'hpo'
    )


class CommentAdmin(admin.ModelAdmin):
    list_display = ('created', 'user', 'flagged',)
    search_fields = ('user', 'comment',)


class EvidenceAdmin(admin.ModelAdmin):
    list_display = ('created', 'name', 'rating',)  # FIXME display last active panel
    search_fields = ('name', 'comment',)


class EvaluationAdmin(admin.ModelAdmin):
    list_display = ('created', 'user', 'rating')
    search_fields = ('user', 'rating', 'publications', 'phenotypes', 'moi', 'version',)


class TrackRecordAdmin(admin.ModelAdmin):
    list_display = ('created', 'user', 'issue_type', 'gel_status')
    search_fields = ('user', 'issue_type', 'issue_description',)


class GenePanelAdmin(admin.ModelAdmin):
    list_display = ('created', 'name', 'approved')
    search_fields = (
        'created',
        'name',
        'genepanelsnapshot_set__level4title__level3title',
        'genepanelsnapshot_set__level4title__level2title',
        'old_panels'
    )


class GenePanelSnapshotAdmin(admin.ModelAdmin):
    list_display = ('created', 'name', 'major_version', 'minor_version')
    search_fields = (
        'created',
        'name',
        'level4title__level3title',
        'level4title__level2title',
        'old_panels',
    )

    def name(self, obj):
        return obj.panel.name


class GenePanelEntrySnapshotAdmin(admin.ModelAdmin):
    ordering = (
        '-created',
    )
    list_display = (
        'created',
        'name',
        'version',
        'saved_gel_status',
        'flagged',
        'ready'
    )
    search_fields = (
        'created',
        'panel__name',
        'panel__level4title__level3title',
        'panel__level4title__level2title',
        'panel__old_panels',
        'comments__text',
    )

    def name(self, obj):
        return obj.panel.panel.name

    def version(self, obj):
        return obj.panel.version


class UploadedGeneListAdmin(admin.ModelAdmin):
    list_display = ('created', 'imported', 'gene_list')


class UploadedPanelListAdmin(admin.ModelAdmin):
    list_display = ('created', 'imported', 'panel_list')


class UploadedReviewsListAdmin(admin.ModelAdmin):
    list_display = ('created', 'imported', 'reviews')


admin.site.register(Tag, TagAdmin)
admin.site.register(Gene, GeneAdmin)
admin.site.register(Activity, ActivityAdmin)
admin.site.register(Level4Title, Level4TitleAdmin)
admin.site.register(Comment, CommentAdmin)
admin.site.register(Evidence, EvidenceAdmin)
admin.site.register(Evaluation, EvaluationAdmin)
admin.site.register(TrackRecord, TrackRecordAdmin)
admin.site.register(GenePanel, GenePanelAdmin)
admin.site.register(GenePanelSnapshot, GenePanelSnapshotAdmin)
admin.site.register(GenePanelEntrySnapshot, GenePanelEntrySnapshotAdmin)
admin.site.register(UploadedGeneList, UploadedGeneListAdmin)
admin.site.register(UploadedPanelList, UploadedPanelListAdmin)
admin.site.register(UploadedReviewsList, UploadedReviewsListAdmin)
