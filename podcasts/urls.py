from django.conf.urls import url

from . import views


urlpatterns = [
    url(r'^$', views.home, name='home'),
    url(r'^dashboard$', views.dashboard, name='dashboard'),
    url(r'^dashboard/podcast/(?P<podcast_slug>[\w-]+)$', views.podcast_dashboard, name='podcast_dashboard'),
    url(r'^dashboard/podcast/(?P<podcast_slug>[\w-]+)/new_episode$', views.podcast_new_ep, name='new_episode'),

    url(r'^listen/(?P<episode_id>[\w]+)', views.listen, name='listen'),
    url(r'^feed/(?P<podcast_slug>[\w-]+)$', views.feed),
]
