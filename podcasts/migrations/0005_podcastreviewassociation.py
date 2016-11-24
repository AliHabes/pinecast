# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('podcasts', '0004_auto_20150723_1539'),
    ]

    operations = [
        migrations.CreateModel(
            name='PodcastReviewAssociation',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('service', models.CharField(max_length=16, choices=[(b'ITUNES', b'iTunes'), (b'STITCHER', b'Stitcher Radio')])),
                ('payload', models.CharField(max_length=256)),
                ('podcast', models.ForeignKey(to='podcasts.Podcast')),
            ],
        ),
    ]
