from __future__ import absolute_import

from django.contrib import admin

from .models import Podcast, PodcastEpisode


admin.site.register(Podcast)
admin.site.register(PodcastEpisode)
