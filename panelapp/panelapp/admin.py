from django.contrib import admin
from django.contrib.sites.models import Site
from markdownx.admin import MarkdownxModelAdmin
from .models import HomeText
from .models import Image
from .models import File


admin.site.site_header = 'PanelApp administration'


class HomeTextAdmin(MarkdownxModelAdmin):
    list_display = ('section', 'href', 'title')


class ImageAdmin(admin.ModelAdmin):
    list_display = ('pk', 'alt', 'title',)
    readonly_fields = ('view_example',)

    def view_example(self, obj):
        "Example of how to use this image with markdown syntax"

        site = Site.objects.get_current()
        return "![{0}](https://{1}{2})".format(obj.alt, site.domain, obj.image.url)

    view_example.empty_value_display = ''
    view_example.short_description = 'Markdown example'


class FileAdmin(admin.ModelAdmin):
    list_display = ('pk', 'title',)
    readonly_fields = ('view_example',)

    def view_example(self, obj):
        "File url"

        site = Site.objects.get_current()
        return "[{0}](https://{1}{2})".format(obj.title, site.domain, obj.file.url)

    view_example.empty_value_display = ''
    view_example.short_description = 'File url'


admin.site.register(HomeText, HomeTextAdmin)
admin.site.register(Image, ImageAdmin)
admin.site.register(File, FileAdmin)
