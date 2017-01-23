from __future__ import absolute_import

from functools import wraps

from django.utils.translation import ugettext

import accounts.payment_plans as plans
from .constants import SOURCE_MAP
from .formatter import Format
from .util import format_ip_list, restrict, specific_location_timeframe
from pinecast.helpers import get_object_or_404
from podcasts.models import PodcastEpisode


def requires_episode(view):
    @wraps(view)
    def wrapper(req, pod, *args, **kwargs):
        print(pod, req.GET.get('episode'))
        ep = get_object_or_404(PodcastEpisode, podcast=pod, id=req.GET.get('episode'))
        return view(req, pod, *args, ep=ep, **kwargs)
    return wrapper


@restrict(plans.FEATURE_MIN_GEOANALYTICS_EP)
@requires_episode
def episode_listener_locations(req, pod, ep):
    f = (Format(req, 'listen-country')
            .select(podcast_f='count')
            .where(episode=str(ep.id))
            .group('country'))

    return f.format_country(label=ugettext('Listeners'))

@restrict(plans.PLAN_PRO)
@specific_location_timeframe
@requires_episode
def episode_listener_locations_specific(req, pod, ep, iso_code):
    f = (Format(req, 'listen-country')
            .select(ip=True)
            .where(episode=str(ep.id), country=iso_code)
            .during('yesterday'))
    return format_ip_list(f, 'city')


@restrict(plans.PLAN_DEMO)
@requires_episode
def episode_listen_history(req, pod, ep):
    f = (Format(req, 'listen')
            .select(episode_f='count')
            .last_thirty()
            .where(episode=str(ep.id)))

    return f.format_interval(label=ugettext('Listens'))


@restrict(plans.PLAN_DEMO)
@requires_episode
def episode_listen_breakdown(req, pod, ep):
    f = (Format(req, 'listen')
            .select(episode_f='count')
            .group('source')
            .last_thirty()
            .where(episode=str(ep.id)))

    return f.format_breakdown(SOURCE_MAP)
