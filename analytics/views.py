from django.utils.translation import ugettext

import accounts.payment_plans as plans
from . import query
from .constants import AGENT_MAP, OS_MAP, SOURCE_MAP
from .formatter import Format
from .util import country_code_map, format_ip_list, restrict, specific_location_timeframe
from accounts.models import UserSettings
from pinecast.helpers import reverse
from podcasts.models import PodcastEpisode


@restrict(plans.PLAN_PRO)
def podcast_subscriber_locations(req, pod):
    f = (Format(req, 'subscription-country')
            .select(podcast_f='count')
            .where(podcast=str(pod.id))
            .during('yesterday')
            .group('country'))

    return f.format_country(label=ugettext('Subscribers'))


@restrict(plans.PLAN_PRO)
def podcast_subscriber_locations_specific_source(req, pod):
    return [
        {'label': country_code_map[x], 'value': x} for x in
        Format(req, 'subscription-country')
                .select(v='count')
                .where(podcast=str(pod.id))
                .during('yesterday', force=True)
                .group('country')
                .get_resulting_groups()]

@restrict(plans.PLAN_PRO)
@specific_location_timeframe
def podcast_subscriber_locations_specific(req, pod, iso_code):
    f = (Format(req, 'subscription-country')
            .select(ip=True)
            .where(podcast=str(pod.id), country=iso_code)
            .during('yesterday', force=True))
    return format_ip_list(f, 'city')


@restrict(plans.FEATURE_MIN_GEOANALYTICS)
def podcast_listener_locations(req, pod):
    f = (Format(req, 'listen-country')
            .select(podcast_f='count')
            .where(podcast=str(pod.id))
            .last_thirty()
            .group('country'))

    return f.format_country(label=ugettext('Listens'))


@restrict(plans.PLAN_PRO)
def podcast_listener_locations_specific_source(req, pod):
    return [
        {'label': country_code_map[x], 'value': x} for x in
        Format(req, 'listen-country')
            .select(v='count')
            .where(podcast=str(pod.id))
            .during('sixmonth', force=True)
            .group('country')
            .get_resulting_groups()]

@restrict(plans.PLAN_PRO)
@specific_location_timeframe
def podcast_listener_locations_specific(req, pod, iso_code):
    f = (Format(req, 'listen-country')
            .select(ip=True)
            .where(podcast=str(pod.id), country=iso_code)
            .during('yesterday'))
    return format_ip_list(f, 'city')


@restrict(plans.PLAN_DEMO)
def podcast_subscriber_history(req, pod):
    f = (Format(req, 'subscription')
            .select(podcast_f='count')
            .last_thirty()
            .where(podcast=str(pod.id)))

    return f.format_interval(label=ugettext('Subscribers'))


@restrict(plans.PLAN_DEMO)
def podcast_listen_history(req, pod):
    f = (Format(req, 'listen')
            .select(episode_f='count')
            .last_thirty()
            .group('podcast')
            .where(podcast=str(pod.id)))

    return f.format_interval(label=ugettext('Listens'))


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
    f = (Format(req, 'listen-platform')
            .select(podcast_f='count')
            .group('browser')
            .last_thirty()
            .where(podcast=str(pod.id)))

    return f.format_breakdown(AGENT_MAP)

@restrict(plans.PLAN_STARTER)
def podcast_listen_os_breakdown(req, pod):
    f = (Format(req, 'listen-platform')
            .select(podcast_f='count')
            .group('os')
            .last_thirty()
            .where(podcast=str(pod.id)))

    return f.format_breakdown(OS_MAP)


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
