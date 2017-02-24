import datetime
import json
import re
from urllib.parse import urlparse

import rollbar
from django.conf import settings
from django.http import Http404, HttpResponse
from django.views.decorators.csrf import csrf_exempt

import analytics.log as analytics_log
from .jinja2_helper import thumbnail
from .helpers import get_object_or_404, json_response, reverse
from accounts.models import UserSettings
from accounts.payment_plans import PLAN_DEMO
from podcasts.models import PodcastEpisode
from podcasts.urls import LISTEN_REGEX


ts_formats = ['[%d/%b/%Y:%H:%M:%S %z]',
              '[%d/%b/%Y:%H:%M:%S +0000]',
              '[%d/%m/%Y:%H:%M:%S +0000]']  # For cdn

@csrf_exempt
def log(req):
    if req.GET.get('access') != settings.LAMBDA_ACCESS_SECRET:
        return HttpResponse(status=400)

    try:
        parsed = json.loads(req.POST['payload'])
    except Exception:
        return HttpResponse(status=400)

    # Make sure we don't iterate over something that's not iterable
    if not isinstance(parsed, list):
        return HttpResponse(status=400)

    listens_to_log = []

    for blob in parsed:
        try:
            ep = PodcastEpisode.objects.get(id=blob['episode'])
        except PodcastEpisode.DoesNotExist:
            continue

        raw_ts = blob.get('ts')
        ts = None
        for f in ts_formats:
            try:
                ts = datetime.datetime.strptime(raw_ts, f)
                break
            except ValueError:
                continue
        else:
            # If we couldn't parse the timestamp, whatever.
            rollbar.report_message('Got unparseable date: %s' % raw_ts, 'error')
            continue

        lo = analytics_log.get_listen_obj(
            ep=ep,
            source=blob.get('source'),
            ip=blob.get('ip'),
            ua=blob.get('userAgent'),
            timestamp=ts)

        if lo:
            listens_to_log.append(lo)

    analytics_log.commit_listens(listens_to_log)

    return HttpResponse(status=204)


@json_response
def oembed(req):
    url = req.GET.get('url')
    if not url:
        raise Http404()

    try:
        path = urlparse(url).path
    except Exception:
        raise Http404()

    if path.startswith('/listen/'):
        try:
            ep_id = re.match(LISTEN_REGEX, path[1:]).group('episode_id')
        except Exception:
            raise Http404()

        ep = get_object_or_404(PodcastEpisode.objects.select_related('podcast'), id=ep_id)
        print(ep)

    else:
        raise Http404()

    us = UserSettings.get_from_user(ep.podcast.owner)
    if us.plan == PLAN_DEMO:
        raise Http404()

    return {
        'version': '1.0',
        'type': 'rich',
        'provider_name': 'Pinecast',
        'provider_url': 'https://pinecast.com',

        'title': ep.title,
        'description': ep.get_html_description(),
        'html': '''
            <iframe src="https://pinecast.com{player}" seamless height="60" style="border:0" class="pinecast-embed" frameborder="0"></iframe>
        '''.format(player=reverse('player', episode_id=str(ep.id))).strip(),
        'height': 60,
        'width': '100%',

        'author_name': ep.podcast.author_name,

        'thumbnail_url': thumbnail(ep.image_url or ep.podcast.cover_image, 500, 500),
        'thumbnail_width': 500,
        'thumbnail_height': 500,
    }
