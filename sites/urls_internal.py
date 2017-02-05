from __future__ import absolute_import

from django.conf import settings
from django.conf.urls import include, url
from django.http import HttpResponse

from . import views


urlpatterns = [
    url(r'^/?$', views.site_home, name='site_home'),
    url(r'^rss/blog$', views.BlogRSS(), name='blog_rss'),
    url(r'^blog/?$', views.site_blog, name='site_blog'),
    url(r'^blog/(?P<post_slug>[\w-]+)$', views.site_post, name='site_post'),
    url(r'^episode/(?P<episode_id>[\w-]+)$', views.site_episode, name='site_episode'),
    url(r'^robots.txt$', lambda req, podcast_slug: HttpResponse('Sitemap: sitemap.xml\n')),
    url(r'^sitemap.xml$', views.sitemap, name='site_sitemap'),
    url(r'^favicon.ico$', views.favicon, name='site_favicon'),
    url(r'^(?P<page_slug>[\w-]+)$', views.site_page, name='site_page'),
]

if settings.DEBUG_TOOLBAR:
    import debug_toolbar
    urlpatterns += (url(r'^__debug__/', include(debug_toolbar.urls)), )
