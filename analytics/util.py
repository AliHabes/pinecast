from __future__ import absolute_import

import requests
import rollbar

from pinecast.types import StringTypes


def escape(val):
    if isinstance(val, StringTypes):
        return "'%s'" % val.replace("'", "\\'")
    elif isinstance(val, (int, float)):
        return str(val)

    raise Exception('Unknown type %s' % type(val))

def ident(val):
    return '"%s"' % val.replace('"', '\\"')


def get_country(ip, req=None):
    if req and req.META.get('HTTP_CF_IPCOUNTRY'):
        return req.META.get('HTTP_CF_IPCOUNTRY').upper()
    if ip == '127.0.0.1':
        return 'US'

    return geoip_lookup_bulk([ip])[0]['code']

def geoip_lookup_bulk(ips):
    try:
        res = requests.post('https://geoip.service.pinecast.com/bulk', json=ips, timeout=4)
        return res.json()
    except Exception as e:
        rollbar.report_message('[pinecast geoip] Error resolving country IP (%s): %s' % (ip, str(e)), 'error')
        return None
