from __future__ import absolute_import

from django.conf.urls import url

from . import views


urlpatterns = [
    url(r'(?P<podcast_slug>[\w-]+)/$', views.podcast_comment_box, name='podcast_comment_box'),
    url(r'(?P<podcast_slug>[\w-]+)/(?P<episode_id>[\w-]+)$', views.ep_comment_box, name='ep_comment_box'),
]
