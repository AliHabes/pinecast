from __future__ import absolute_import

from django.conf.urls import url

from . import views


urlpatterns = [
    url(r'^feed/(?P<podcast_slug>[\w-]+)$', views.feed, name='feed'),
    url(r'^listen/(?P<episode_id>[\w-]+)(\.mp3)?$', views.listen, name='listen'),
    url(r'^player/(?P<episode_id>[\w-]+)$', views.player, name='player'),
]
