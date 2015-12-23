import datetime
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils.translation import ugettext, ugettext_lazy

import accounts.payment_plans as plans
from formatter import Format
from . import query
from accounts.models import Network, UserSettings
from dashboard.views import get_podcast
from pinecast.helpers import json_response
from podcasts.models import Podcast, PodcastEpisode


def restrict(minimum_plan):
    def wrapped(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            req = args[0]
            if not req.user:
                return HttpResponseForbidden()

            pod = get_podcast(req, req.GET.get('podcast'))

            uset = UserSettings.get_from_user(pod.owner)
            if not plans.minimum(uset.plan, minimum_plan):
                return HttpResponseForbidden()

            resp = view(req, pod, *args[1:], **kwargs)
            if not isinstance(resp, (dict, list, bool, str, unicode, int, float)):
                # Handle HttpResponse/HttpResponseBadRequest/etc
                return resp
            return JsonResponse(resp, safe=False)
        return wrapper
    return wrapped


@restrict(plans.PLAN_PRO)
def podcast_subscriber_locations(req, pod):
    f = (Format(req, 'subscribe')
            .select(podcast='count')
            .where(podcast=pod.id)
            .during('yesterday')
            .group('profile.country'))

    return f.format_country()


@restrict(plans.FEATURE_MIN_GEOANALYTICS)
def podcast_listener_locations(req, pod):
    f = (Format(req, 'listen')
            .select(podcast='count')
            .where(podcast=pod.id)
            .last_thirty()
            .group('profile.country'))

    return f.format_country(label=ugettext('Listeners'))

@restrict(plans.FEATURE_MIN_GEOANALYTICS_EP)
def episode_listener_locations(req, pod):
    ep = get_object_or_404(PodcastEpisode, podcast=pod, id=req.GET.get('episode'))
    f = (Format(req, 'listen')
            .select(podcast='count')
            .where(episode=ep.id)
            .group('profile.country'))

    return f.format_country(label=ugettext('Listeners'))


@restrict(plans.PLAN_DEMO)
def podcast_subscriber_history(req, pod):
    f = (Format(req, 'subscribe')
            .select(podcast='count')
            .last_thirty()
            .where(podcast=pod.id))

    return f.format_intervals(label=pod.name)


@restrict(plans.PLAN_DEMO)
def podcast_listen_history(req, pod):
    f = (Format(req, 'listen')
            .select(podcast='count')
            .last_thirty()
            .where(podcast=pod.id))

    return f.format_intervals(label=pod.name)


@restrict(plans.PLAN_DEMO)
def episode_listen_history(req, pod):
    ep = get_object_or_404(PodcastEpisode, podcast=pod, id=req.GET.get('episode'))
    f = (Format(req, 'listen')
            .select(episode='count')
            .last_thirty()
            .where(episode=ep.id))

    return f.format_intervals(label=ep.title)


SOURCE_MAP = {
    'direct': ugettext_lazy('Direct'),
    'rss': ugettext_lazy('Subscription'),
    'embed': ugettext_lazy('Embedded Player'),
    None: ugettext_lazy('Unknown'),
}

@restrict(plans.PLAN_DEMO)
def podcast_listen_breakdown(req, pod):
    f = (Format(req, 'listen')
            .select(podcast='count')
            .group('source')
            .last_thirty()
            .where(podcast=pod.id))

    return f.format_breakdown(SOURCE_MAP)


@restrict(plans.PLAN_STARTER)
def podcast_listen_platform_breakdown(req, pod):
    breakdown_type = req.GET.get('breakdown_type', 'device')
    if breakdown_type not in ['device', 'browser', 'os']: raise Http404()

    f = (Format(req, 'listen')
            .select(podcast='count')
            .group(['profile.%s' % breakdown_type])
            .last_thirty()
            .where(podcast=pod.id))

    return f.format_breakdown(None)


@restrict(plans.PLAN_PRO)
def episode_listen_breakdown(req, pod):
    ep = get_object_or_404(PodcastEpisode, podcast=pod, id=req.GET.get('episode'))
    f = (Format(req, 'listen')
            .select(episode='count')
            .group('source')
            .last_thirty()
            .where(episode=ep.id))

    return f.format_breakdown(SOURCE_MAP)


@login_required
@json_response
def network_listen_history(req):
    net = get_object_or_404(Network, id=req.GET.get('network_id'), members__in=[req.user])

    pods = net.podcast_set.all()
    async_queries = [
        Format(req, 'listen', async=True)
            .select(podcast='count')
            .last_thirty()
            .interval()
            .where(podcast=pod.id) for
        pod in
        pods
    ]
    Format.async_resolve_all(async_queries)

    labels, datasets = Format.format_intervals_bulk(
        async_queries,
        lambda d: d.strftime('%x'),
        pick='podcast'
    )

    formatted_datasets = []
    for i, dataset in enumerate(datasets):
        pod = pods[i]
        formatted_datasets.append({
            'label': pod.name,
            'data': dataset,
            'fillColor': 'transparent',
            'strokeColor': '#303F9F',
            'pointColor': '#3F51B5',
            'pointStrokeColor': '#fff',
        })

    return {
        'labels': labels,
        'datasets': list(
            query.rotating_colors(formatted_datasets,
                                  key='strokeColor',
                                  highlight_key='pointColor')
        ),
    }
