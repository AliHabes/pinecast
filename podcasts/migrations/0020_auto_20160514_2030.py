# -*- coding: utf-8 -*-
from __future__ import absolute_import
# Generated by Django 1.9 on 2016-05-14 20:30
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('podcasts', '0019_podcastepisode_flair_tip_jar'),
    ]

    operations = [
        migrations.AlterField(
            model_name='podcast',
            name='networks',
            field=models.ManyToManyField(blank=True, to='accounts.Network'),
        ),
    ]
