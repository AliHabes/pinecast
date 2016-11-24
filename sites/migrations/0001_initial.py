# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('podcasts', '0006_auto_20150730_2343'),
    ]

    operations = [
        migrations.CreateModel(
            name='Site',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('slug', models.SlugField(unique=True)),
                ('theme', models.CharField(max_length=16, choices=[(b'panther', 'Panther'), (b'podcasty', 'Podcasty'), (b'zen', 'Zen'), (b'wharf', 'Wharf'), (b'abn', 'ABN')])),
                ('custom_cname', models.CharField(max_length=64, null=True, blank=True)),
                ('logo_url', models.URLField(blank=True)),
                ('itunes_url', models.URLField(blank=True)),
                ('stitcher_url', models.URLField(blank=True)),
                ('podcast', models.OneToOneField(to='podcasts.Podcast')),
            ],
        ),
        migrations.CreateModel(
            name='SiteBlogPost',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(max_length=512)),
                ('slug', models.SlugField()),
                ('created', models.DateTimeField(auto_now=True)),
                ('publish', models.DateTimeField()),
                ('body', models.TextField()),
                ('site', models.ForeignKey(to='sites.Site')),
            ],
        ),
        migrations.CreateModel(
            name='SiteLink',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(max_length=256)),
                ('url', models.URLField(blank=True)),
                ('class_name', models.CharField(max_length=256, null=True, blank=True)),
                ('site', models.ForeignKey(to='sites.Site')),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='siteblogpost',
            unique_together=set([('site', 'slug')]),
        ),
    ]
