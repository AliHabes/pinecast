from __future__ import absolute_import
from __future__ import print_function

import datetime
import json

import rollbar
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

import analytics.log as analytics_log
from podcasts.models import PodcastEpisode


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

    print(('Logging %d listen records' % len(listens_to_log)))
    analytics_log.commit_listens(listens_to_log)

    return HttpResponse(status=204)
