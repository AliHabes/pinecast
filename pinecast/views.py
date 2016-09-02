import datetime
import json

import requests
import rollbar
from django.conf import settings
from django.http import Http404, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

import analytics.analyze as analyze
import analytics.log as analytics_log
from podcasts.models import Podcast, PodcastEpisode


@csrf_exempt
@require_POST
def deploy_complete(req):

    commit = '<https://github.com/AlmostBetterNetwork/pinecast/commit/%s|%s>' % (
        req.POST.get('head'), req.POST.get('head'))

    payload = {
        'text': '''
            Hey guys! I'm Pinecast version %s. I was just born! :hatching_chick:
You have %s to thank for pushing %s to production.
To learn about what's new, check out #pinecast :two_hearts:
        '''.strip() % (req.POST.get('release'), req.POST.get('user'), commit),
        'username': 'newborn-pinecast',
        'icon_emoji': ':cat2:',
    }

    print requests.post(
        settings.DEPLOY_SLACKBOT_URL,
        data={'payload': json.dumps(payload)})

    return HttpResponse(status=204)


class FakeReq(object):
    def __init__(self, blob):
        self.META = {'HTTP_USER_AGENT': blob['userAgent'],
                     'REMOTE_ADDR': blob['ip']}


@csrf_exempt
def log(req):
    if req.GET.get('access') != settings.LAMBDA_ACCESS_SECRET:
        return HttpResponse(status=400)

    try:
        parsed = json.loads(req.POST.get('payload'))
    except Exception:
        return HttpResponse(status=400)

    ts_formats = ['[%d/%b/%Y:%H:%M:%S %z]',
                  '[%d/%b/%Y:%H:%M:%S +0000]',
                  '[%d/%m/%Y:%H:%M:%S +0000]']  # For cdn

    listens_to_log = []

    # Make sure we don't iterate over something that's not iterable
    try:
        assert list(parsed)
    except Exception:
        return HttpResponse(status=400)

    for blob in parsed:
        fr = FakeReq(blob)
        if analyze.is_bot(fr):
            continue

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

        # If we couldn't parse the timestamp, whatever.
        if not ts:
            rollbar.report_message('Got unparseable date: %s' % raw_ts, 'error')
            continue

        browser, device, os = analyze.get_device_type(fr)
        print 'Logging record of listen for %s' % unicode(ep.id)

        listens_to_log.append({
            'podcast': unicode(ep.podcast.id),
            'episode': unicode(ep.id),
            'source': blob.get('source'),
            'profile': {
                'ip': blob.get('ip'),
                'ua': blob.get('userAgent'),
                'browser': browser,
                'device': device,
                'os': os,
            },

            'timestamp': ts.isoformat(),
        })

    analytics_log.write_many('listen', listens_to_log)

    return HttpResponse(status=204)
