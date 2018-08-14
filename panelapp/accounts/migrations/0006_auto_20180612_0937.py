# -*- coding: utf-8 -*-
# Generated by Django 1.11.6 on 2018-06-12 08:37
from __future__ import unicode_literals

from django.db import migrations
from django.db.models import Q
from panelapp.models import HomeText
from panelapp.models import Image
from panelapp.models import File
from panels.models import UploadedGeneList
from panels.models import UploadedPanelList
from panels.models import UploadedReviewsList

user_support_group = 'User Support'
site_editor_group = 'Site Editor'
file_upload_curation_group = 'File Upload Curation'


def create_panelapp_groups(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')
    ContentType = apps.get_model('contenttypes', 'ContentType')
    User = apps.get_model('accounts', 'User')
    Reviewer = apps.get_model('accounts', 'Reviewer')

    user_content_type = ContentType.objects.get_for_model(User)
    reviewer_content_type = ContentType.objects.get_for_model(Reviewer)

    user_support = Group.objects.create(name=user_support_group)
    user_support.permissions.set(
        Permission.objects.filter(
            Q(content_type=user_content_type) | Q(content_type=reviewer_content_type)
        )
    )

    hometext_content_type = ContentType.objects.get_for_model(HomeText)
    image_content_type = ContentType.objects.get_for_model(Image)
    file_content_type = ContentType.objects.get_for_model(File)
    site_editor = Group.objects.create(name=site_editor_group)
    site_editor.permissions.set(
        Permission.objects.filter(
            Q(content_type=hometext_content_type) | Q(content_type=image_content_type) | Q(content_type=file_content_type)
        )
    )

    gene_list_content_type = ContentType.objects.get_for_model(UploadedGeneList)
    panel_list_content_type = ContentType.objects.get_for_model(UploadedPanelList)
    reviews_list_content_type = ContentType.objects.get_for_model(UploadedReviewsList)
    site_editor = Group.objects.create(name=file_upload_curation_group)
    site_editor.permissions.set(
        Permission.objects.filter(
            Q(content_type=gene_list_content_type) | Q(content_type=panel_list_content_type) | Q(
                content_type=reviews_list_content_type)
        )
    )


def delete_panelapp_groups(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.filter(name=user_support_group).delete()
    Group.objects.filter(name=site_editor_group).delete()
    Group.objects.filter(name=file_upload_curation_group).delete()



class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_auto_20170816_0954'),
    ]

    operations = [
        migrations.RunPython(create_panelapp_groups, delete_panelapp_groups),
    ]