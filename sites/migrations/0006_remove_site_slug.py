# -*- coding: utf-8 -*-
# Generated by Django 1.9 on 2016-01-17 00:11
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sites', '0005_auto_20150823_2041'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='site',
            name='slug',
        ),
    ]