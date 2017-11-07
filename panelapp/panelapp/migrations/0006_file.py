# -*- coding: utf-8 -*-
# Generated by Django 1.11.6 on 2017-11-06 17:29
from __future__ import unicode_literals

from django.db import migrations, models
import panelapp.utils.storage


class Migration(migrations.Migration):

    dependencies = [
        ('panelapp', '0005_auto_20170620_1600'),
    ]

    operations = [
        migrations.CreateModel(
            name='File',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.FileField(max_length=512, storage=panelapp.utils.storage.OverwriteStorage(), upload_to='files')),
                ('title', models.CharField(max_length=128, verbose_name='File title')),
            ],
        ),
    ]
