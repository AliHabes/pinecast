import collections
import json
import os.path

import requests
import rollbar
from functools import wraps

from django.http import HttpResponseBadRequest, HttpResponseForbidden, JsonResponse

import accounts.payment_plans as plans
from accounts.models import UserSettings
from dashboard.views import get_podcast
from pinecast.types import StringTypes


def get_country(ip, req=None):
    if req and req.META.get('HTTP_CF_IPCOUNTRY'):
        return req.META.get('HTTP_CF_IPCOUNTRY').upper()
    if ip == '127.0.0.1':
        return 'US'

    lookup = geoip_lookup_bulk([ip])
    if not lookup or not lookup[0] or not lookup[0]['code']:
        return None
    return lookup[0]['code']

def geoip_lookup_bulk(ips):
    try:
        res = requests.post('https://geoip.service.pinecast.com:444/bulk', json=ips, timeout=4)
        return res.json()
    except Exception as e:
        rollbar.report_message('[pinecast geoip] Error resolving country IP (%s): %s' % (ip, str(e)), 'error')
        return None


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


def format_ip_list(formatter, label):
    ip_counter = collections.Counter(formatter.get_resulting_value('ip'))
    ip_counts = ip_counter.most_common(200)

    lookups = geoip_lookup_bulk([x for x, _ in ip_counts])

    def extend(x, **kw):
        x.update(kw)
        return x

    geo_index = {
        (x['lat'], x['lon']): extend(x, lat=float(x['lat']), lon=float(x['lon'])) for
        x in lookups if x and x['zip']}
    c = collections.Counter()
    for i, x in enumerate(lookups):
        if not x or not x['zip']:
            continue
        c[(x['lat'], x['lon'])] += ip_counts[i][1]

    return [dict(count=count, **geo_index[coord], label=geo_index[coord][label]) for coord, count in c.items()]


country_codes = json.load(open(os.path.join(os.path.dirname(__file__), 'country_codes.json')))
country_code_map = {x['Code']: x['Name'] for x in country_codes}
