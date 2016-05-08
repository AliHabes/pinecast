# -*- coding: utf-8 -*-
# Generated by Django 1.9 on 2016-05-08 23:35
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('podcasts', '0016_auto_20160503_0324'),
    ]

    operations = [
        migrations.AddField(
            model_name='podcastepisode',
            name='flair_feedback',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='podcastepisode',
            name='flair_powered_by',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='podcastepisode',
            name='flair_site_link',
            field=models.BooleanField(default=False),
        ),
    ]
