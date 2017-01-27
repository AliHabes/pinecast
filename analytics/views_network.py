from functools import wraps

from .formatter import Format
from .util import country_code_map, format_ip_list, specific_location_timeframe
from accounts.models import Network
from pinecast.helpers import get_object_or_404, json_response


def requires_network(view):
    @wraps(view)
    def wrapper(req, pod, *args, **kwargs):
        net = get_object_or_404(Network, id=req.GET.get('network_id'), members__in=[req.user])
        return view(req, pod, *args, net=net, **kwargs)
    return json_response(wrapper)


@requires_network
def network_listen_history(req, net):
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


@requires_network
def network_subscriber_history(req, net):
    net = get_object_or_404(Network, id=req.GET.get('network_id'), members__in=[req.user])

    pods = net.podcast_set.all()

    f = (Format(req, 'subscription')
            .select(podcast_f='count')
            .last_thirty()
            .interval()
            .group('podcast')
            .where(podcast=[str(p.id) for p in pods]))

    return f.format_intervals(
        labels_map={str(p.id): p.name for p in pods},
        extra_data={str(p.id): {'slug': p.slug} for p in pods})


@requires_network
def network_subscriber_locations(req, net):
    f = (Format(req, 'subscription-country')
            .select(podcast_f='count')
            .where(podcast=[str(pod.id) for pod in net.podcast_set.all()])
            .during('yesterday')
            .group('country'))

    return f.format_country(label=ugettext('Subscribers'))

@requires_network
def network_subscriber_locations_specific_source(req, net):
    return [
        {'label': country_code_map[x], 'value': x} for x in
        Format(req, 'subscription-country')
                .select(v='count')
                .where(podcast=[str(pod.id) for pod in net.podcast_set.all()])
                .during('yesterday', force=True)
                .group('country')
                .get_resulting_groups()]

@requires_network
@specific_location_timeframe
def network_subscriber_locations_specific(req, net, iso_code):
    f = (Format(req, 'subscription-country')
            .select(ip=True)
            .where(
                podcast=[str(pod.id) for pod in net.podcast_set.all()],
                country=iso_code,
            )
            .during('yesterday', force=True))
    return format_ip_list(f, 'city')

@requires_network
def network_listener_locations(req, net):
    f = (Format(req, 'listen-country')
            .select(podcast_f='count')
            .where(podcast=[str(pod.id) for pod in net.podcast_set.all()])
            .last_thirty()
            .group('country'))

    return f.format_country(label=ugettext('Listens'))

@requires_network
def network_listener_locations_specific_source(req, net):
    return [
        {'label': country_code_map[x], 'value': x} for x in
        Format(req, 'listen-country')
            .select(v='count')
            .where(podcast=[str(pod.id) for pod in net.podcast_set.all()])
            .during('sixmonth', force=True)
            .group('country')
            .get_resulting_groups()]

@requires_network
@specific_location_timeframe
def network_listener_locations_specific(req, net, iso_code):
    f = (Format(req, 'listen-country')
            .select(ip=True)
            .where(
                podcast=[str(pod.id) for pod in net.podcast_set.all()],
                country=iso_code,
            )
            .during('yesterday'))
    return format_ip_list(f, 'city')
