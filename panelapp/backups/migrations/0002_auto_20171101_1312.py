# -*- coding: utf-8 -*-
# Generated by Django 1.11.6 on 2017-11-01 13:12
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backups', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='panelbackup',
            options={'ordering': ['-major_version', '-minor_version']},
        ),
        migrations.AddIndex(
            model_name='panelbackup',
            index=models.Index(fields=['name'], name='backups_pan_name_76f29c_idx'),
        ),
        migrations.AddIndex(
            model_name='panelbackup',
            index=models.Index(fields=['old_pk'], name='backups_pan_old_pk_c3c8b6_idx'),
        ),
        migrations.AddIndex(
            model_name='panelbackup',
            index=models.Index(fields=['original_pk'], name='backups_pan_origina_56e97b_idx'),
        ),
        migrations.AddIndex(
            model_name='panelbackup',
            index=models.Index(fields=['major_version'], name='backups_pan_major_v_fd3413_idx'),
        ),
        migrations.AddIndex(
            model_name='panelbackup',
            index=models.Index(fields=['minor_version'], name='backups_pan_minor_v_1760d5_idx'),
        ),
    ]