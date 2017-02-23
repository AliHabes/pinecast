from __future__ import absolute_import

from django.conf.urls import url

from . import views


LISTEN_REGEX = r'^listen/(?P<episode_id>[\w-]+)(\.mp3)?$'

urlpatterns = [
    url(r'^feed/(?P<podcast_slug>[\w-]+)$', views.feed, name='feed'),
    url(r'^feed/(?P<podcast_slug>[\w-]+)/sub/(?P<subscriber>[\w-]+)$', views.feed_private, name='feed_private'),
    url(LISTEN_REGEX, views.listen, name='listen'),
    url(r'^player/(?P<episode_id>[\w-]+)$', views.player, name='player'),
    url(r'^embed/player_latest/(?P<podcast_slug>[\w-]+)$', views.player_latest, name='player_latest'),
]
