from django.conf.urls import url

from . import views, views_episode, views_network


urlpatterns = [
    # New
    url(r'^podcast/listens$', views.podcast_listen_history),
    url(r'^podcast/listens/location$', views.podcast_listener_locations),
    url(r'^podcast/listens/location/options$', views.podcast_listener_locations_specific_source),
    url(r'^podcast/listens/location/(?P<iso_code>[A-Z0-9]{2})$', views.podcast_listener_locations_specific),
    url(r'^podcast/listens/breakdown$', views.podcast_listen_breakdown),
    url(r'^podcast/listens/agent$', views.podcast_listen_platform_breakdown),
    url(r'^podcast/listens/os$', views.podcast_listen_os_breakdown),
    url(r'^podcast/listens/top-episodes$', views.podcast_top_episodes),
    url(r'^podcast/subscribers$', views.podcast_subscriber_history),
    url(r'^podcast/subscribers/location$', views.podcast_subscriber_locations),
    url(r'^podcast/subscribers/location/options$', views.podcast_subscriber_locations_specific_source),
    url(r'^podcast/subscribers/location/(?P<iso_code>[A-Z0-9]{2})$', views.podcast_subscriber_locations_specific),

    url(r'^episode/listens$', views_episode.episode_listen_history),
    url(r'^episode/listens/breakdown$', views_episode.episode_listen_breakdown),
    url(r'^episode/listens/location$', views_episode.episode_listener_locations),
    url(r'^episode/listens/location/options$', views_episode.episode_listener_locations_specific_source),
    url(r'^episode/listens/location/(?P<iso_code>[A-Z0-9]{2})$', views_episode.episode_listener_locations_specific),

    url(r'^network/listens$', views_network.network_listen_history),
    url(r'^network/listens/location$', views_network.network_listener_locations),
    url(r'^network/listens/location/options$', views_network.network_listener_locations_specific_source),
    url(r'^network/listens/location/(?P<iso_code>[A-Z0-9]{2})$', views_network.network_listener_locations_specific),
    url(r'^network/subscribers$', views_network.network_subscriber_history),
    url(r'^network/subscribers/location$', views_network.network_subscriber_locations),
    url(r'^network/subscribers/location/options$', views_network.network_subscriber_locations_specific_source),
    url(r'^network/subscribers/location/(?P<iso_code>[A-Z0-9]{2})$', views_network.network_subscriber_locations_specific),

]
