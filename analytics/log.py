import datetime
import hashlib
import json

import requests
import rollbar
from django.conf import settings
from influxdb import InfluxDBClient

from .analyze import get_device_type, get_request_hash, get_request_ip, is_bot


influx_databases = {
    'subscribe': settings.INFLUXDB_DB_SUBSCRIPTION,
    'subscription': settings.INFLUXDB_DB_SUBSCRIPTION,
    'listen': settings.INFLUXDB_DB_LISTEN,
}

def get_influx_item(measurement, tags, fields, timestamp=None):
    if not timestamp:
        timestamp = datetime.datetime.now()
    return {
        'measurement': measurement,
        'tags': tags,
        'fields': dict(v=1, **fields),
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
    try:
        return influx_client.write_points(items, database=db)
    except Exception as e:
        if settings.DEBUG: raise e
        rollbar.report_message('Problem delivering logs to influx: %s' % e, 'error')
        return None


def write_gc_many(collection, blobs):
    if settings.DISABLE_GETCONNECT:
        return

    try:
        posted = requests.post(
            'https://api.getconnect.io/events',
            timeout=15,
            data=json.dumps({collection: blobs}),
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


def write_listen(*args, **kwargs):
    obj = get_listen_obj(*args, **kwargs)
    if not obj:
        return
    commit_listens([obj])

def get_listen_obj(ep, source, req=None, ip=None, ua=None, timestamp=None):
    if is_bot(req=req, ua=ua): return None

    if not ip: ip = get_request_ip(req)
    if not ua: ua = req.META.get('HTTP_USER_AGENT')
    if not timestamp: timestamp = datetime.datetime.now()

    ep_id = unicode(ep.id)
    pod_id = unicode(ep.podcast.id)

    browser, device, os = get_device_type(req=req, ua=ua)
    country = _get_country(ip, req)

    gc_listen = {
        'podcast': pod_id,
        'episode': ep_id,
        'source': source,
        'profile': {
            'country': country,
            'ip': ip,
            'ua': ua,
            'browser': browser,
            'device': device,
            'os': os,
        },
        'timestamp': timestamp.isoformat(),
    }


    base_tags = {
        'podcast': pod_id,
        'episode': ep_id,
    }
    base_fields = {
        'podcast_f': pod_id,
        'episode_f': ep_id,

        'ip': ip,
        'ua': ua,

        'l_id': hashlib.sha1(','.join([ip, ua, timestamp.isoformat()])).hexdigest(),
    }
    points = [
        get_influx_item(
            measurement='listen',
            tags=dict(
                source=source,
                **base_tags
            ),
            fields=base_fields,
            timestamp=timestamp,
        ),
        get_influx_item(
            measurement='listen-platform',
            tags=dict(
                browser=browser,
                os=os,
                **base_tags
            ),
            fields=base_fields,
            timestamp=timestamp,
        ),
    ]
    if country:
        points.append(
            get_influx_item(
                measurement='listen-country',
                tags=dict(
                    country=country,
                    **base_tags
                ),
                fields=base_fields,
                timestamp=timestamp,
            )
        )

    return gc_listen, points


def commit_listens(listen_objs):
    gc_listens = [x[0] for x in listen_objs]
    write_gc_many('listen', gc_listens)

    points = [i for _, y in listen_objs for i in y]
    write_influx_many(settings.INFLUXDB_DB_LISTEN, points)


def write_subscription(req, podcast):
    if is_bot(req=req): return

    ip = get_request_ip(req)
    ua = req.META.get('HTTP_USER_AGENT')

    pod_id = unicode(podcast.id)

    browser, device, os = get_device_type(req=req, ua=ua)
    country = _get_country(ip, req)

    gc_subscription = {
        'id': get_request_hash(req),
        'podcast': pod_id,
        'profile': {
            'country': country,
            'ip': ip,
            'ua': ua,
            'browser': browser,
            'device': device,
            'os': os,
        },
    }
    write_gc_many('subscribe', [gc_subscription])

    influx_ts = datetime.datetime.combine(datetime.date.today(), datetime.time.min)

    base_tags = {
        'podcast': pod_id,
    }
    base_fields = {
        'podcast_f': pod_id,
        'ip': ip,
        'ua': ua,
        'l_id': hashlib.sha1(','.join([ip, ua, influx_ts.isoformat()])).hexdigest(),
    }

    points = [
        get_influx_item(
            measurement='subscription',
            tags=dict(
                browser=browser,
                os=os,
                **base_tags
            ),
            fields=base_fields,
            timestamp=influx_ts,
        ),
    ]
    if country:
        points.append(
            get_influx_item(
                measurement='subscription-country',
                tags=dict(
                    country=country,
                    **base_tags
                ),
                fields=base_fields,
                timestamp=influx_ts,
            )
        )

    write_influx_many(settings.INFLUXDB_DB_SUBSCRIPTION, points)
