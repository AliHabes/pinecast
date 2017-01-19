from __future__ import absolute_import

import collections
import datetime
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponseForbidden, JsonResponse
from django.shortcuts import render
from django.utils.translation import ugettext, ugettext_lazy

import accounts.payment_plans as plans
from . import query
from .formatter import Format
from .util import geoip_lookup_bulk
from accounts.models import Network, UserSettings
from dashboard.views import get_podcast
from pinecast.helpers import get_object_or_404, json_response, reverse
from pinecast.types import StringTypes
from podcasts.models import Podcast, PodcastEpisode


ACCEPTABLE_TIMEFRAMES = {
    'all': None,
    'month': {'previous': {'hours': 30 * 24}},
    'week': {'previous': {'hours': 7 * 24}},
    'day': {'previous': {'hours': 24}},
}


def restrict(minimum_plan):
    def wrapped(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            req = args[0]
            if not req.user:
                return HttpResponseForbidden()

            pod = get_podcast(req, req.GET.get('podcast'))

            uset = UserSettings.get_from_user(pod.owner)
            if (not plans.minimum(uset.plan, minimum_plan) and
                not req.user.is_staff):
                return HttpResponseForbidden()

            resp = view(req, pod, *args[1:], **kwargs)
            if not isinstance(resp, (dict, list, bool, int, float) + StringTypes) and resp is not None:
                # Handle HttpResponse/HttpResponseBadRequest/etc
                return resp
            return JsonResponse(resp, safe=False)
        return wrapper
    return wrapped


SPECIFIC_LOCATION_TIMEFRAMES = ['day', 'yesterday', 'week', 'month']

def specific_location_timeframe(view):
    @wraps(view)
    def wrapped(req, *args, **kwargs):
        if req.GET.get('timeframe', 'day') not in SPECIFIC_LOCATION_TIMEFRAMES:
            return HttpResponseBadRequest()
        result = view(req, *args, **kwargs)
        return result
    return wrapped

def format_ip_list(formatter):
    ip_counter = collections.Counter(formatter.get_resulting_value('ip'))
    ip_counts = ip_counter.most_common(200)

    lookups = geoip_lookup_bulk([x for x, _ in ip_counts])
    geo_index = {(x['lat'], x['lon']): x for x in lookups if x and x['zip']}
    c = collections.Counter()
    for i, x in enumerate(lookups):
        if not x or not x['zip']:
            continue
        c[(x['lat'], x['lon'])] += ip_counts[i][1]

    return [dict(count=count, **geo_index[coord]) for coord, count in c.items()]


@restrict(plans.PLAN_PRO)
def podcast_subscriber_locations(req, pod):
    f = (Format(req, 'subscription-country')
            .select(podcast_f='count')
            .where(podcast=str(pod.id))
            .during('yesterday')
            .group('country'))

    return f.format_country()

@restrict(plans.PLAN_PRO)
@specific_location_timeframe
def podcast_subscriber_locations_specific(req, pod, iso_code):
    f = (Format(req, 'subscription-country')
            .select(ip=True)
            .where(podcast=str(pod.id), country=iso_code)
            .during('yesterday'))
    return format_ip_list(f)

@restrict(plans.FEATURE_MIN_GEOANALYTICS)
def podcast_listener_locations(req, pod):
    f = (Format(req, 'listen-country')
            .select(podcast_f='count')
            .where(podcast=str(pod.id))
            .last_thirty()
            .group('country'))

    return f.format_country(label=ugettext('Listeners'))

@restrict(plans.PLAN_PRO)
@specific_location_timeframe
def podcast_listener_locations_specific(req, pod, iso_code):
    f = (Format(req, 'listen-country')
            .select(ip=True)
            .where(podcast=str(pod.id), country=iso_code)
            .during('yesterday'))
    return format_ip_list(f)

@restrict(plans.FEATURE_MIN_GEOANALYTICS_EP)
def episode_listener_locations(req, pod):
    ep = get_object_or_404(PodcastEpisode, podcast=pod, id=req.GET.get('episode'))
    f = (Format(req, 'listen-country')
            .select(podcast_f='count')
            .where(episode=str(ep.id))
            .group('country'))

    return f.format_country(label=ugettext('Listeners'))

@restrict(plans.PLAN_PRO)
@specific_location_timeframe
def episode_listener_locations_specific(req, pod, iso_code):
    ep = get_object_or_404(PodcastEpisode, podcast=pod, id=req.GET.get('episode'))
    f = (Format(req, 'listen-country')
            .select(ip=True)
            .where(episode=str(ep.id), country=iso_code)
            .during('yesterday'))
    return format_ip_list(f)


@restrict(plans.PLAN_DEMO)
def podcast_subscriber_history(req, pod):
    f = (Format(req, 'subscription')
            .select(podcast_f='count')
            .last_thirty()
            .where(podcast=str(pod.id)))

    return f.format_interval()


@restrict(plans.PLAN_DEMO)
def podcast_listen_history(req, pod):
    f = (Format(req, 'listen')
            .select(episode_f='count')
            .last_thirty()
            .group('podcast')
            .where(podcast=str(pod.id)))

    return f.format_interval()


@restrict(plans.PLAN_DEMO)
def episode_listen_history(req, pod):
    ep = get_object_or_404(PodcastEpisode, podcast=pod, id=req.GET.get('episode'))
    f = (Format(req, 'listen')
            .select(episode_f='count')
            .last_thirty()
            .where(episode=str(ep.id)))

    return f.format_interval()


SOURCE_MAP = {
    'direct': ugettext_lazy('Direct'),
    'rss': ugettext_lazy('Subscription'),
    'embed': ugettext_lazy('Player'),
    None: ugettext_lazy('Unknown'),
}

@restrict(plans.PLAN_DEMO)
def podcast_listen_breakdown(req, pod):
    f = (Format(req, 'listen')
            .select(podcast_f='count')
            .group('source')
            .last_thirty()
            .where(podcast=str(pod.id)))

    return f.format_breakdown(SOURCE_MAP)


@restrict(plans.PLAN_STARTER)
def podcast_listen_platform_breakdown(req, pod):
    breakdown_type = req.GET.get('breakdown_type', 'browser')
    if breakdown_type not in ['browser', 'os']: raise Http404()

    f = (Format(req, 'listen-platform')
            .select(podcast_f='count')
            .group(breakdown_type)
            .last_thirty()
            .where(podcast=str(pod.id)))

    return f.format_breakdown()


@restrict(plans.PLAN_DEMO)
def episode_listen_breakdown(req, pod):
    ep = get_object_or_404(PodcastEpisode, podcast=pod, id=req.GET.get('episode'))
    f = (Format(req, 'listen')
            .select(episode_f='count')
            .group('source')
            .last_thirty()
            .where(episode=str(ep.id)))

    return f.format_breakdown(SOURCE_MAP)


@json_response
def network_listen_history(req):
    net = get_object_or_404(Network, id=req.GET.get('network_id'), members__in=[req.user])

    pods = net.podcast_set.all()

    f = (Format(req, 'listen')
            .select(episode_f='count')
            .last_thirty()
            .interval()
            .group('podcast')
            .where(podcast=[str(p.id) for p in pods]))

    return f.format_intervals(
        labels_map={str(p.id): p.name for p in pods},
        extra_data={str(p.id): {'slug': p.slug} for p in pods})


@restrict(plans.PLAN_PRO)
def podcast_top_episodes(req, pod):
    timeframe = req.GET.get('timeframe')
    if not timeframe:
        return None

    tz = UserSettings.get_from_user(req.user).tz_offset
    top_ep_data = query.get_top_episodes(str(pod.id), timeframe, tz)
    episodes = PodcastEpisode.objects.filter(id__in=list(top_ep_data.keys()))
    mapped = {str(ep.id): ep for ep in episodes}

    # This step is necessary to filter out deleted episodes, since deleted episodes
    # are not removed from the analytics data.
    top_ep_data = {k: v for k, v in top_ep_data.items() if k in mapped}

    # Sort the top episode data descending
    return [[ugettext('Episode'), ugettext('Count')]] + [
        [
            {
                'href': reverse('podcast_episode', podcast_slug=pod.slug, episode_id=ep_id),
                'title': mapped[ep_id].title,
            },
            count,
        ] for
        ep_id, count in
        list(reversed(sorted(top_ep_data.items(), key=lambda x: x[1])))[:25]
    ]
