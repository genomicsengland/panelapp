# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2017-08-16 08:54
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_auto_20170530_1414'),
    ]

    operations = [
        migrations.AlterField(
            model_name='reviewer',
            name='affiliation',
            field=models.CharField(max_length=1024),
        ),
    ]