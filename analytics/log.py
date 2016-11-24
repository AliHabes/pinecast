from __future__ import absolute_import
from __future__ import print_function

import datetime
import hashlib
import json

import requests
import rollbar
from django.conf import settings

from .analyze import get_device_type, get_request_hash, get_request_ip, get_ts_hash, is_bot
from .influx import get_client
from .query import total_listens
from notifications.models import NotificationHook
from pinecast.types import StringTypes


def get_influx_item(measurement, tags, fields, timestamp=None):
    if not timestamp:
        timestamp = datetime.datetime.now()
    return {
        'measurement': measurement,
        'tags': tags,
        'fields': dict(v=1, **fields),
        'time': timestamp.isoformat(),
        'ts_raw': timestamp,
    }

def write_influx(db, *args):
    return write_influx_many(db, [get_influx_item(*args)])

def write_influx_many(db, items):
    influx_client = get_client()

    return influx_client.write_points(items, database=db)
    try:
        return influx_client.write_points(list(_strip_ts_raw(items)), database=db)
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
    except requests.exceptions.Timeout:
        # fuck getconnect
        return
    except Exception as e:
        rollbar.report_message('Analytics POST error: %s' % str(e), 'error')
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
    if not ua: ua = req.META.get('HTTP_USER_AGENT', 'Unknown') or 'Unknown'
    if not timestamp: timestamp = datetime.datetime.now()

    ep_id = str(ep.id)
    pod_id = str(ep.podcast.id)

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

        'l_id': hashlib.sha1(','.join([ip, ua, timestamp.isoformat()]).encode('utf-8')).hexdigest(),
    }
    points = [
        # commit_listens below relies on the main listen to be first in this array
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


LISTEN_HOOKS = ['first_listen', 'listen_threshold', 'growth_milestone']

def commit_listens(listen_objs):
    if not listen_objs:
        return
    podcasts = set(x[0]['tags']['podcast'] for _, x in listen_objs)
    hooks = list(NotificationHook.objects.filter(
                podcast_id__in=list(podcasts),
                trigger__in=LISTEN_HOOKS))
    podcasts_with_hooks = set(str(h.podcast_id) for h in hooks)
    episodes = set(
        (x[0]['tags']['podcast'], x[0]['tags']['episode']) for
        _, x in
        listen_objs if
        x[0]['tags']['podcast'] in podcasts_with_hooks)

    pod_listens_before = {p: total_listens(p) for p in podcasts_with_hooks}
    ep_listens_before = {e: (p, total_listens(p, e)) for p, e in episodes}

    write_gc_many('listen', [x[0] for x in listen_objs])
    write_influx_many(
        settings.INFLUXDB_DB_LISTEN, [i for _, y in listen_objs for i in y])

    if not podcasts_with_hooks:
        return

    notifications = {p: [n for n in hooks if str(n.podcast_id) == p] for p in podcasts_with_hooks}

    from podcasts.models import PodcastEpisode
    ep_cache = {}
    def get_ep(ep_id):
        if ep_id in ep_cache:
            return ep_cache.get(ep_id)
        else:
            ep = PodcastEpisode.objects.get(id=ep_id)
            ep_cache[ep_id] = ep
            return ep

    def notify_all(notifications, body={}):
        if not notifications:
            return
        for notification in notifications:
            notification.execute(body)

    # Handle first_listen notifications
    if any(hook.trigger == 'first_listen' for hook in hooks):
        for ep_id, (pod_id, count) in ep_listens_before.items():
            if count:
                continue
            matching_hooks = [h for h in notifications[pod_id] if h.trigger == 'first_listen']
            if not matching_hooks:
                continue
            notify_all(matching_hooks, {'episode': get_ep(ep_id)})

    # Handle listen_threshold
    if any(hook.trigger == 'listen_threshold' for hook in hooks):
        for ep_id, (pod_id, count) in ep_listens_before.items():
            matching_hooks = [h for h in notifications[pod_id] if h.trigger == 'listen_threshold']
            if not matching_hooks:
                continue
            new_count = total_listens(pod_id, ep_id)
            notify_all(
                [h for h in matching_hooks if h.test_condition(count, new_count)],
                {'episode': get_ep(ep_id), 'listens': new_count})

    # Handle growth_milestone
    if any(hook.trigger == 'growth_milestone' for hook in hooks):
        for pod_id, count in pod_listens_before.items():
            matching_hooks = [h for h in notifications[pod_id] if h.trigger == 'growth_milestone']
            if not matching_hooks:
                continue
            new_count = total_listens(pod_id)
            notify_all(
                [h for h in matching_hooks if h.test_condition(count, new_count)],
                {'listens': new_count, 'before_listens': count})


def write_subscription(req, podcast, ts=None, dry_run=False):
    if is_bot(req=req):
        if settings.DEBUG:
            print(('Ignoring bot: %s' % req.META.get('HTTP_USER_AGENT')))
        return

    ip = get_request_ip(req)
    ua = req.META.get('HTTP_USER_AGENT', 'Unknown') or 'Unknown'

    if isinstance(podcast, StringTypes):
        pod_id = podcast
    else:
        pod_id = str(podcast.id)

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

    influx_ts = ts or datetime.datetime.combine(datetime.date.today(), datetime.time.min)
    hashed_influx_ts = influx_ts + datetime.timedelta(microseconds=get_ts_hash(ip, ua, influx_ts))

    base_tags = {
        'podcast': pod_id,
    }
    base_fields = {
        'podcast_f': pod_id,
        'ip': ip,
        'ua': ua,
        'l_id': hashlib.sha1(','.join([ip, ua, influx_ts.isoformat()]).encode('utf-8')).hexdigest(),
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
            timestamp=hashed_influx_ts,
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
                timestamp=hashed_influx_ts,
            )
        )

    if dry_run:
        return

    write_gc_many('subscribe', [gc_subscription])
    result = write_influx_many(settings.INFLUXDB_DB_SUBSCRIPTION, points)
    if not result:
        if settings.DEBUG:
            print('Error ingesting data to InfluxDB')
        else:
            rollbar.report_message(
                'Unable to ingest subscription points to influx', 'error')


def write_notification(notification, failed, is_test=False):
    write_influx(
        settings.INFLUXDB_DB_NOTIFICATION,
        'notification',
        {
            'podcast': str(notification.podcast.id),
            'notification': str(notification.id),
            'destination_type': notification.destination_type,
            'trigger': notification.trigger,
        },
        {
            'notification_f': str(notification.id),
            'failed': failed,
            'is_test': 'true' if is_test else 'false',
        })
