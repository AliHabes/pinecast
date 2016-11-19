import datetime

import gfm
from django.contrib.syndication.views import Feed
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.http import HttpResponse
from django.shortcuts import redirect, render

from . import models
from accounts.models import UserSettings
from accounts.payment_plans import FEATURE_MIN_SITE_FAVICON, minimum
from podcasts.models import Podcast, PodcastEpisode
from pinecast.helpers import get_object_or_404, reverse

import urls_internal


SITE_EPISODES_PER_PAGE = 5


def _subdomain_reverse(*args, **kwargs):
    if 'podcast_slug' in kwargs:
        del kwargs['podcast_slug']
    return reverse(urlconf=urls_internal, *args, **kwargs)

def _srender(req, site, template, data=None):

    data = data or {}
    data.setdefault('site', site)
    if 'site_hostname' in req.META:
        data['url'] = _subdomain_reverse
        data['url_global'] = reverse
    return render(req, 'sites/%s/%s' % (site.theme, template), data)


def site_home(req, podcast_slug):
    pod = get_object_or_404(Podcast, slug=podcast_slug)
    site = get_object_or_404(models.Site, podcast=pod)
    episodes = pod.get_episodes()
    paginator = Paginator(episodes, SITE_EPISODES_PER_PAGE)
    try:
        pager = paginator.page(req.GET.get('page'))
    except PageNotAnInteger:
        pager = paginator.page(1)
    except EmptyPage:
        return redirect('site_home', podcast_slug=pod.slug)
    return _srender(req, site, 'home.html', {'pager': pager})


def site_blog(req, podcast_slug):
    pod = get_object_or_404(Podcast, slug=podcast_slug)
    site = get_object_or_404(models.Site, podcast=pod)
    posts = site.siteblogpost_set.filter(
        publish__lt=datetime.datetime.now()).order_by('-publish')
    paginator = Paginator(posts, 5)
    try:
        pager = paginator.page(req.GET.get('page'))
    except PageNotAnInteger:
        pager = paginator.page(1)
    except EmptyPage:
        return redirect('site_home', podcast_slug=pod.slug)
    return _srender(req, site, 'blog.html', {'pager': pager})

def site_post(req, podcast_slug, post_slug):
    pod = get_object_or_404(Podcast, slug=podcast_slug)
    site = get_object_or_404(models.Site, podcast=pod)
    post = get_object_or_404(models.SiteBlogPost, site=site, slug=post_slug)
    return _srender(req, site, 'post.html', {'post': post})

def site_episode(req, podcast_slug, episode_id):
    pod = get_object_or_404(Podcast, slug=podcast_slug)
    site = get_object_or_404(models.Site, podcast=pod)
    episode = get_object_or_404(PodcastEpisode, podcast=site.podcast, id=episode_id)
    return _srender(req, site, 'episode.html', {'episode': episode})


class BlogRSS(Feed):

    def get_object(self, req, podcast_slug):
        pod = get_object_or_404(Podcast, slug=podcast_slug)
        return get_object_or_404(models.Site, podcast=pod)

    def title(self, obj):
        return obj.podcast.name

    def link(self, obj):
        return _subdomain_reverse('site_home', podcast_slug=obj.podcast.slug)

    def description(self, obj):
        return obj.podcast.description

    def items(self, obj):
        return obj.siteblogpost_set.order_by('-publish')

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        return gfm.markdown(item.body)

    def item_link(self, item):
        return _subdomain_reverse('site_post', podcast_slug=item.site.podcast.slug, post_slug=item.slug)

    item_guid_is_permalink = True

    def item_author_name(self, item):
        return item.site.podcast.author_name

    def item_pubdate(self, item):
        return item.publish

    def item_copyright(self, item):
        return item.site.podcast.copyright


def sitemap(req, podcast_slug):
    pod = get_object_or_404(Podcast, slug=podcast_slug)
    site = get_object_or_404(models.Site, podcast=pod)

    output = '''<?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    '''

    pages = pod.podcastepisode_set.all().count()
    for i in xrange(pages):
        output += '''
        <url>
            <loc>{url}</loc>
            <changefreq>weekly</changefreq>
        </url>
        '''.format(url='%s?page=%d' % (
            _subdomain_reverse('site_home', podcast_slug=pod.slug),
            i + 1))

    output += '''
    <url><loc>{url}</loc></url>
    '''.format(url=_subdomain_reverse('site_blog', podcast_slug=pod.slug))

    for episode in pod.podcastepisode_set.all():
        output += '''
        <url><loc>{url}</loc></url>
        '''.format(url=_subdomain_reverse('site_episode', podcast_slug=pod.slug, episode_id=str(episode.id)))

    for post in site.siteblogpost_set.all():
        output += '''
        <url><loc>{url}</loc></url>
        '''.format(url=_subdomain_reverse('site_post', podcast_slug=pod.slug, post_slug=post.slug))


    output += '</urlset>'

    return HttpResponse(output, content_type='application/xml')

def favicon(req, podcast_slug):
    pod = get_object_or_404(Podcast, slug=podcast_slug)
    us = UserSettings.get_from_user(pod.owner)
    if not minimum(us.plan, FEATURE_MIN_SITE_FAVICON):
        return redirect('https://pinecast.com/static/img/favicon.png')

    site = get_object_or_404(models.Site, podcast=pod)

    if not site.favicon_url:
        return redirect('https://pinecast.com/static/img/favicon.png')

    return redirect(site.favicon_url)
