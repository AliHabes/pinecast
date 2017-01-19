from __future__ import absolute_import

from django.conf.urls import url

from . import views


urlpatterns = [
    url(r'^podcast-subscriber-locations$', views.podcast_subscriber_locations),
    url(r'^podcast-subscriber-locations/(?P<iso_code>[A-Z0-9]{2})$', views.podcast_subscriber_locations_specific),
    url(r'^podcast-listener-locations$', views.podcast_listener_locations),
    url(r'^episode-listener-locations$', views.episode_listener_locations),
    url(r'^podcast-subscriber-history$', views.podcast_subscriber_history),
    url(r'^podcast-listen-history$', views.podcast_listen_history),
    url(r'^episode-listen-history$', views.episode_listen_history),
    url(r'^podcast-listen-breakdown$', views.podcast_listen_breakdown),
    url(r'^podcast-listen-platform-breakdown$', views.podcast_listen_platform_breakdown),
    url(r'^episode-listen-breakdown$', views.episode_listen_breakdown),

    url(r'^podcast-top-episodes$', views.podcast_top_episodes),

    url(r'^network-listen-history$', views.network_listen_history),
]
