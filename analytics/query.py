import collections
import datetime
import json

import grequests
from django.conf import settings


def query_async(collection, q):
    if 'timeframe' not in q and 'timezone' in q:
        del q['timezone']
    return grequests.get(
        'https://api.getconnect.io/events/%s' % collection,
        timeout=2,
        params={'query': json.dumps(q)},
        headers={'X-Project-Id': settings.GETCONNECT_IO_PID,
                 'X-Api-Key': settings.GETCONNECT_IO_QUERY_KEY})

def query_async_resolve(async_queries):
    if isinstance(async_queries, list):
        out = []
        for x in grequests.map(async_queries):
            try:
                out.append(x.json())
                x.close()
            except (ValueError, AttributeError):
                pass
        return out

    elif isinstance(async_queries, dict):
        items = async_queries.items()
        results = []
        # Don't pass `.values()`. There's no guarantee that the values will be
        # returned in the same order as `.items()`. It's also an extra
        # unnecessary call.
        for x in grequests.map(v for k, v in items):
            try:
                results.append(x.json())
                x.close()
            except ValueError:
                pass

        return {k: results[i] for i, (k, v) in enumerate(items)}

    raise Exception('Unknown type passed to query_async_resolve')


class AsyncContext(object):
    def __init__(self):
        self.pending = []
        self.resolved = None

    def add(self, item, processor, default=None):
        self.pending.append(item)
        idx = len(self.pending) - 1

        return lambda: processor(self.resolve()[idx])

    def resolve(self):
        if self.resolved:
            return self.resolved

        self.resolved = []
        for x in grequests.map(self.pending):
            if not x:
                self.resolved.append({})
                continue
            try:
                self.resolved.append(x.json())
                x.close()
            except ValueError:
                pass

        return self.resolved

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        if traceback: return
        self.resolve()


def total_listens(podcast, async, episode_id=None):
    q = {'select': {'podcast': 'count'},
         'filter': {'podcast': unicode(podcast.id)}}
    if episode_id:
        q['filter']['episode'] = episode_id
    data = query_async('listen', q)
    base_listens = 0 if episode_id is not None else podcast.stats_base_listens

    def get_listens(data):
        if ('results' not in data or
            not data['results'] or
            'podcast' not in data['results'][0]):
            return base_listens

        return data['results'][0]['podcast'] + base_listens

    return async.add(data, get_listens)


def total_listens_this_week(podcast, async):
    data = query_async(
        'listen',
        {'select': {'episode': 'count'},
         'timeframe': {'previous': {'hours': 7 * 24}},
         'filter': {'podcast': {'eq': unicode(podcast.id)}}})

    def get_listens(data):
        if ('results' not in data or
            not data['results'] or
            'episode' not in data['results'][0]):
            return -1
        return data['results'][0]['episode']

    return async.add(data, get_listens)


def total_subscribers(podcast, async):
    data = query_async(
        'subscribe',
        {'select': {'podcast': 'count'},
         'timeframe': 'today',
         'filter': {'podcast': {'eq': unicode(podcast.id)}}})

    def get_listens(data):
        if ('results' not in data or
            not data['results'] or
            'podcast' not in data['results'][0]):
            return -1
        return data['results'][0]['podcast']

    return async.add(data, get_listens)


def get_top_episodes(podcast_id, async):
    data = query_async(
        'listen',
        {'select': {'podcast': 'count'},
         'groupBy': 'episode',
         'filter': {'podcast': {'eq': podcast_id}}})

    return async.add(data, lambda d: d['results'] if 'results' in d else [])


def process_groups(groups, label_mapping=None, label_key=None, pick=None):
    if not groups: return []

    if not label_mapping: label_mapping = collections.defaultdict(collections.defaultdict)

    labels = [label_mapping.get(x[label_key], x[label_key]) for x in groups]
    values = groups if not pick else [x[pick] for x in groups]

    return {'labels': labels, 'dataset': values}


def rotating_colors(sequence, key='color', highlight_key='highlight'):
    for x, c in zip(sequence, _colors_forever()):
        x[key] = c
        x[highlight_key] = _colorscale(c, 1.1)
        yield x


def _colors_forever():
    while 1:
        yield '#5395D3'
        yield '#52D1C7'
        yield '#FF9800'
        yield '#4CAF50'
        yield '#FF4081'

        yield '#1abc9c'
        yield '#2ecc71'
        yield '#3498db'
        yield '#9b59b6'
        yield '#34495e'
        yield '#16a085'
        yield '#27ae60'
        yield '#2980b9'
        yield '#8e44ad'
        yield '#2c3e50'
        yield '#f1c40f'
        yield '#e67e22'
        yield '#e74c3c'
        yield '#f39c12'
        yield '#d35400'
        yield '#c0392b'


def _colorscale(hexstr, scalefactor):
    """
    Scales a hex string by ``scalefactor``. Returns scaled hex string.

    To darken the color, use a float value between 0 and 1.
    To brighten the color, use a float value greater than 1.

    >>> colorscale("#DF3C3C", .5)
    #6F1E1E
    >>> colorscale("#52D24F", 1.6)
    #83FF7E
    >>> colorscale("#4F75D2", 1)
    #4F75D2
    """

    hexstr = hexstr.strip('#')

    if scalefactor < 0 or len(hexstr) != 6:
        return hexstr

    r, g, b = int(hexstr[:2], 16), int(hexstr[2:4], 16), int(hexstr[4:], 16)

    r = max(0, min(r * scalefactor, 255))
    g = max(0, min(g * scalefactor, 255))
    b = max(0, min(b * scalefactor, 255))

    return "#%02x%02x%02x" % (r, g, b)
