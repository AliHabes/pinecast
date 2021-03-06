# -*- coding: utf-8 -*-
# Generated by Django 1.10.2 on 2017-02-09 17:12
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0005_collaborator'),
    ]

    operations = [
        migrations.AlterField(
            model_name='collaborator',
            name='collaborator',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='collaborated_podcasts', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='collaborator',
            name='podcast',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='collaborators', to='podcasts.Podcast'),
        ),
    ]
