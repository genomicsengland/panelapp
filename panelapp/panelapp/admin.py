from django.contrib import admin
from markdownx.admin import MarkdownxModelAdmin
from .models import HomeText
from .models import Image


class HomeTextAdmin(MarkdownxModelAdmin):
    list_display = ('section', 'href', 'title')


admin.site.register(HomeText, HomeTextAdmin)
admin.site.register(Image)
