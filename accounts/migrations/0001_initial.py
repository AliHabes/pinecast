# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='BetaRequest',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(auto_now=True)),
                ('email', models.EmailField(max_length=254)),
                ('podcaster_type', models.CharField(max_length=8, choices=[(b'HOBBYIST', b'Hobbyist'), (b'AUTHOR', b'Author or Writer'), (b'MUSICIAN', b'Musician'), (b'RADIO', b'Radio Personality'), (b'COMEDY', b'Comedian'), (b'POLITIC', b'Politician')])),
            ],
        ),
        migrations.CreateModel(
            name='Network',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=256)),
                ('created', models.DateTimeField(auto_now=True)),
                ('image_url', models.URLField(blank=True)),
                ('members', models.ManyToManyField(to=settings.AUTH_USER_MODEL)),
                ('owner', models.ForeignKey(related_name='network_ownership', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='UserSettings',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('plan', models.PositiveIntegerField(default=0, choices=[(0, b'Demo'), (1, b'Starter'), (2, b'Pro'), (3, b'Ultimate')])),
                ('tz_offset', models.SmallIntegerField(default=0)),
                ('user', models.OneToOneField(to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
