import datetime
import json

import requests
import rollbar
from django.conf import settings
from influxdb import InfluxDBClient


influx_databases = {
    'subscribe': settings.INFLUXDB_DB_SUBSCRIPTION,
    'subscription': settings.INFLUXDB_DB_SUBSCRIPTION,
    'listen': settings.INFLUXDB_DB_LISTEN,
}

def get_influx_item(db, tags, fields, timestamp=None):
    if not timestamp:
        timestamp = datetime.datetime.now()
    return {
        'measurement': influx_databases[db],
        'tags': tags,
        'fields': fields,
        'time': timestamp.isoformat() + 'Z',
    }

def write_influx(db, *args):
    return write_influx_many(db, [get_influx_item(db, *args)])

def write_influx_many(db, items):
    influx_client = InfluxDBClient(
        host='influx.service.pinecast.com',
        port=443,
        username=settings.INFLUXDB_USERNAME,
        password=settings.INFLUXDB_PASSWORD,
        ssl=True,
        verify_ssl=True,
        timeout=10)

    for item in items:
        if 'ip' in item['fields']:
            country = _get_country(item['fields']['ip'])
            if not country:
                continue
            item['fields']['country_f'] = country
            item['tags']['country'] = country

    try:
        return influx_client.write_points(items, database=influx_databases[db])
    except Exception as e:
        rollbar.report_message('Problem delivering logs to influx: %s' % e, 'error')
        return None


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
            timeout=7.5,
            data=payload,
            headers={'X-Project-Id': settings.GETCONNECT_IO_PID,
                     'X-Api-Key': settings.GETCONNECT_IO_PUSH_KEY})
    except Exception:
        rollbar.report_message('Analytics POST timeout: %s' % url, 'error')
        return

    # 409 is a duplicate ID error, which is expected
    if posted.status_code != 200 and posted.status_code != 409:
        rollbar.report_message(
            'Got non-200 status code submitting logs: %s %s' % (
                posted.status_code,
                posted.text),
            'error')

def _get_country(ip, req=None):
    if req and req.META.get('HTTP_CF_IPCOUNTRY'):
        return req.META.get('HTTP_CF_IPCOUNTRY').upper()
    if ip == '127.0.0.1':
        return 'US'
    try:
        res = requests.get('http://geoip.nekudo.com/api/%s' % ip)
        parsed = res.json()
        if not parsed['country']:
            return None
        return parsed['country']['code']
    except Exception as e:
        rollbar.report_message('Error resolving country IP (%s): %s' % (ip, str(e)), 'error')
        return None
