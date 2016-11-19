from django.conf.urls import url
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
]
