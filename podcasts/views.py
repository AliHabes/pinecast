import datetime
import time
from email.Utils import formatdate
from xml.sax.saxutils import escape, quoteattr

from django.conf import settings
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render

import accounts.payment_plans as plans
import analytics.analyze as analyze
import analytics.log as analytics_log
from .models import Podcast, PodcastEpisode
from accounts.models import UserSettings
from pinecast.helpers import get_object_or_404


PREMIUM_S3_PREFIX = 'https://%s.s3.amazonaws.com/' % settings.S3_PREMIUM_BUCKET
S3_PREFIX_REPLACEMENT = '%s/' % settings.CDN_HOSTNAME
def _asset(url):
    if url.startswith(PREMIUM_S3_PREFIX):
        url = url.replace(PREMIUM_S3_PREFIX, S3_PREFIX_REPLACEMENT, 1)
    return url


def listen(req, episode_id):
    ep = get_object_or_404(PodcastEpisode, id=episode_id)
    if not analyze.is_bot(req) and req.method == 'GET':
        browser, device, os = analyze.get_device_type(req)
        analytics_log.write('listen', {
            'podcast': unicode(ep.podcast.id),
            'episode': unicode(ep.id),
            'source': 'embed' if req.GET.get('embed') else 'direct',
            'profile': {
                'ip': analyze.get_request_ip(req),
                'ua': req.META.get('HTTP_USER_AGENT'),
                'browser': browser,
                'device': device,
                'os': os,
            },
        }, req=req)

    return redirect(_asset(ep.audio_url))


def feed(req, podcast_slug):
    pod = get_object_or_404(Podcast, slug=podcast_slug)

    if pod.rss_redirect:
        return redirect(pod.rss_redirect, permanent=True)

    items = []
    episodes = pod.get_episodes()
    is_demo = UserSettings.get_from_user(pod.owner).plan == plans.PLAN_DEMO

    for ep in episodes:
        ep_url = _asset(ep.audio_url + '?x-source=rss&x-episode=%s' % str(ep.id))

        md_desc = ep.get_html_description(is_demo=is_demo)

        explicit_tag = ''
        if ep.explicit_override != PodcastEpisode.EXPLICIT_OVERRIDE_CHOICE_NONE:
            explicit_tag = '<itunes:explicit>%s</itunes:explicit>' % (
                'yes' if ep.explicit_override == PodcastEpisode.EXPLICIT_OVERRIDE_CHOICE_EXPLICIT else 'clean')

        items.append('\n'.join([
            '<item>',
            '<title>%s</title>' % escape(ep.title),
            '<description><![CDATA[%s]]></description>' % md_desc,
            '<link>%s</link>' % escape(ep_url),
            '<guid isPermaLink="false">https://pinecast.com/guid/%s</guid>' % escape(str(ep.id)),
            '<pubDate>%s</pubDate>' % formatdate(time.mktime(ep.publish.timetuple())),
            explicit_tag,
            '<itunes:author>%s</itunes:author>' % escape(pod.author_name),
            '<itunes:subtitle>%s</itunes:subtitle>' % escape(ep.subtitle),
            '<itunes:image href=%s />' % quoteattr(_asset(ep.image_url)),
            '<itunes:duration>%s</itunes:duration>' % escape(ep.formatted_duration()),
            '<enclosure url=%s length=%s type=%s />' % (
                quoteattr(ep_url), quoteattr(str(ep.audio_size)), quoteattr(ep.audio_type)),
            ('<dc:copyright>%s</dc:copyright>' % escape(ep.copyright)) if ep.copyright else '',
            ('<dc:rights>%s</dc:rights>' % escape(ep.license)) if ep.license else '',
            '</item>',
        ]))

    categories = sorted([c.category for c in pod.podcastcategory_set.all()], key=lambda c: len(c))
    category_map = {}
    for cat in categories:
        spl = cat.split('/')
        cursor = category_map
        for i in spl:
            cursor.setdefault(i, {})
            cursor = cursor[i]

    def render_cat(c):
        for k, v in c.items():
            if not v:
                yield '<itunes:category text=%s />' % quoteattr(k)
            else:
                yield '<itunes:category text=%s>%s</itunes:category>' % (
                    quoteattr(k), '\n'.join(render_cat(v)))

    content = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss xmlns:atom="http://www.w3.org/2005/Atom"',
        '     xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd"',
        '     xmlns:dc="http://purl.org/dc/elements/1.1/"',
        '     version="2.0">',
        '<channel>',
        '<title>%s</title>' % escape(pod.name),
        '<link>%s</link>' % escape(pod.homepage),
        '<atom:link href="https://pinecast.com/feed/%s" rel="self" type="application/rss+xml" />' % escape(pod.slug),
        '<language>%s</language>' % escape(pod.language),
        '<copyright>%s</copyright>' % escape(pod.copyright),
        '<generator>Pinecast (https://pinecast.com)</generator>',
        ('<itunes:subtitle>%s</itunes:subtitle>' % escape(pod.subtitle)) if pod.subtitle else '',
        '<itunes:author>%s</itunes:author>' % escape(pod.author_name),
        '<description><![CDATA[%s]]></description>' % pod.description,
        '<itunes:owner>',
        '<itunes:name>%s</itunes:name>' % escape(pod.author_name),
        '<itunes:email>%s</itunes:email>' % escape(pod.owner.email),
        '</itunes:owner>',
        '<itunes:explicit>%s</itunes:explicit>' % ('yes' if pod.is_explicit else 'no'),
        '<itunes:image href=%s />' % quoteattr(_asset(pod.cover_image)),
        '\n'.join(render_cat(category_map)),
        '\n'.join(items),
        '</channel>',
        '</rss>',
    ]
    if UserSettings.get_from_user(pod.owner).plan == plans.PLAN_DEMO:
        if len(episodes) > 10:
            content.append('<!-- This feed is truncated because the owner is not a paid customer. -->')
        else:
            content.append('<!-- This feed will be truncated at 10 items because the owner is not a paid customer. -->')

    if not analyze.is_bot(req):
        browser, device, os = analyze.get_device_type(req)
        analytics_log.write('subscribe', {
            'id': analyze.get_request_hash(req),
            'podcast': unicode(pod.id),
            'profile': {
                'ip': analyze.get_request_ip(req),
                'ua': req.META.get('HTTP_USER_AGENT'),
                'browser': browser,
                'device': device,
                'os': os,
            },
        }, req=req)

    resp = HttpResponse('\n'.join(c for c in content if c), content_type='application/rss+xml')
    resp.setdefault('Cache-Control', 'public, max-age=120')
    return resp


def player(req, episode_id):
    ep = get_object_or_404(PodcastEpisode, id=episode_id)
    resp = render(req, 'player.html', {'episode': ep})

    # If the user is not a demo user, allow the player to be used outside the app.
    if UserSettings.user_meets_plan(ep.podcast.owner, plans.FEATURE_MIN_PLAYER):
        resp.xframe_options_exempt = True
    return resp
