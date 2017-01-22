from __future__ import absolute_import

from .formatter import Format
from accounts.models import Network
from pinecast.helpers import get_object_or_404, json_response


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


@json_response
def network_subscriber_history(req):
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
