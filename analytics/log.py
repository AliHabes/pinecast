import json

import requests
import rollbar
from django.conf import settings


def write(collection, blob, req=None):
    if 'profile' in blob and 'ip' in blob['profile']:
        blob['profile']['country'] = _get_country(blob['profile']['ip'], req=req)
    _post('https://api.getconnect.io/events/%s' % collection, json.dumps(blob))


def write_many(collection, blobs, req=None):
    # TODO: Convert this to use requests.async
    for blob in blobs:
        if 'profile' in blob and 'ip' in blob['profile']:
            blob['profile']['country'] = _get_country(blob['profile']['ip'])
    _post('https://api.getconnect.io/events', json.dumps({collection: blobs}))


def _post(url, payload):
    try:
        posted = requests.post(
            url,
            timeout=5,
            data=payload,
            headers={'X-Project-Id': settings.GETCONNECT_IO_PID,
                     'X-Api-Key': settings.GETCONNECT_IO_PUSH_KEY})
    except Exception:
        rollbar.report_message('Analytics POST timeout: %s' % url, 'error')
        return

    if posted.status_code != 200 and posted.status_code != 409:
        rollbar.report_message(
            'Got non-200 status code submitting logs: %s %s' % (
                posted.status_code,
                posted.text),
            'error')
        # 409 is a duplicate ID error, which is expected
        print posted.status_code, posted.text

def _get_country(ip, req=None):
    if req and req.META.get('HTTP_CF_IPCOUNTRY'):
        return req.META.get('HTTP_CF_IPCOUNTRY').upper()
    if ip == '127.0.0.1':
        return 'US'
    try:
        res = requests.get('http://geoip.nekudo.com/api/%s' % ip)
        return res.json()['country']['code']
    except Exception as e:
        rollbar.report_message('Error resolving country IP: %s' % str(e), 'error')
        return None
