import datetime
import re

from django.utils.translation import ugettext

from . import query
from accounts.models import UserSettings


TIMZONE_KILLA = re.compile(r'(\d\d\d\d\-\d\d\-\d\dT\d\d:\d\d:\d\d)[+\-]\d\d:\d\d')

DELTAS = {
    'minutely': datetime.timedelta(minutes=1),
    'hourly': datetime.timedelta(hours=1),
    'daily': datetime.timedelta(days=1),
    'weekly': datetime.timedelta(weeks=1),
    'monthly': datetime.timedelta(weeks=4),
    'quarterly': datetime.timedelta(weeks=4 * 3),
    'yearly': datetime.timedelta(weeks=52),
}

USER_TIMEFRAMES = {
    'day': 'today',
    'yesterday': 'yesterday',  # Should not be exposed in UI
    'week': {'previous': {'hours': 7 * 24}},
    'month': {'previous': {'hours': 30 * 24}},
    'sixmonth': {'previous': {'hours': 6 * 30 * 24}},
    'year': {'previous': {'hours': 12 * 30 * 24}},
    'all': None,
}


class Format(object):
    def __init__(self, req, event_type, async=False):
        self.event_type = event_type
        self.req = req
        self.selection = {}
        self.criteria = {}
        self.timeframe = None
        self.interval_val = None
        self.group_by = None
        self.res = None

        self.async = async
        self.async_query = None

    def select(self, **kwargs):
        self.selection.update(kwargs)
        return self

    def where(self, **kwargs):
        for key, val in kwargs.items():
            if isinstance(val, list):
                self.criteria[key] = {'in': val}
            else:
                self.criteria[key] = val

        return self

    def group(self, by):
        self.group_by = by
        return self

    def during(self, timeframe=None, **kwargs):
        self.timeframe = timeframe or kwargs
        return self

    def last_thirty(self):
        self.timeframe = 'month'
        return self

    def interval(self, value=None):
        self.interval_val = value or self.req.GET.get('interval', 'daily')
        if self.interval_val not in DELTAS:
            self.interval_val = 'daily'
        return self

    def _process(self):
        assert self.selection
        assert not self.async_query
        q = {
            'select': self.selection,
            'timezone': UserSettings.get_from_user(self.req.user).tz_offset,
        }

        if self.criteria:
            q['filter'] = self.criteria
        if self.group_by:
            q['groupBy'] = self.group_by
        if self.timeframe:
            tf = USER_TIMEFRAMES.get(self.req.GET.get('timeframe', self.timeframe))
            if tf:
                q['timeframe'] = tf
        if self.interval_val:
            q['interval'] = self.interval_val

        self.async_query = query.query_async(self.event_type, q)
        if not self.async:
            self.async = query.AsyncContext()
            Format.async_resolve_all([self])
        return self

    def format_country(self, label=None):
        if not self.res: self._process()
        if not self.res or 'results' not in self.res: return []

        key = self.selection.keys()[0]

        return [[ugettext('Country'), label or ugettext('Subscribers')]] + [
            [p[self.group_by], p[key]] for
            p in
            self.res['results'] if
            p[self.group_by] and 'results' in self.res
        ]

    def format_intervals(self, labels, labeled_by=None, extra_data=None, unfiltered=False):
        if not self.interval_val: self.interval()
        if not self.res: self._process()

        if not labeled_by and len(self.criteria) > 1:
            raise Exception('You must pass `labeled_by` to explain disambiguate the criterion to pick')

        if not self.res or 'results' not in self.res or not self.res['results']:
            # TODO: come up with better error handling
            return {'labels': [''],
                    'datasets': [{'label': '', 'data': []}]}

        key = self.selection.keys()[0]

        interval_duration = DELTAS[self.interval_val]
        sformat = '%H:%M' if interval_duration < DELTAS['daily'] else '%x'

        processed = [Interval(x) for x in self.res['results']]
        output_labels = [x.start.strftime(sformat) for x in processed]
        cursor = processed[0].start

        default_facet = labeled_by or self.criteria.keys()[0]

        datasets = []
        dataset_map = {}

        for label_id, label in labels.items():
            ds = {
                'label': label,
                'data': [],
                'id': label_id,
                'pointStrokeColor': '#fff'}
            if extra_data and label_id in extra_data:
                ds.update(extra_data[label_id])
            datasets.append(ds)
            dataset_map[label_id] = ds

        # Process the first interval early
        first_interval = processed.pop(0)
        for ds_id, ds in dataset_map.items():
            for res in first_interval.payload:
                if res[default_facet] == ds_id or unfiltered:
                    ds['data'].append(res.get(key, 0))
                    break
            else:
                ds['data'].append(0)

        cursor += interval_duration

        while processed and cursor <= processed[-1].start:
            current_interval = processed.pop(0)
            for ds_id, ds in dataset_map.items():
                for res in current_interval.payload:
                    if res[default_facet] == ds_id or unfiltered:
                        ds['data'].append(res.get(key, 0))
                        break
                else:
                    ds['data'].append(0)

            cursor += interval_duration

        if not datasets: datasets = [{}]

        datasets = query.rotating_colors(
            datasets,
            key='strokeColor',
            highlight_key='pointColor')

        return {
            'labels': output_labels,
            'datasets': list(datasets),
        }

    def format_breakdown(self, groups):
        if not self.res: self._process()
        if not self.res or 'results' not in self.res: return []  # TODO: come up with better error handling

        key = self.selection.keys()[0]

        out = query.process_groups(
            self.res['results'],
            groups,
            self.group_by if isinstance(self.group_by, str) else self.group_by[0],
            pick=key
        )
        if not out:
            return []

        out = [{'label': unicode(label), 'value': value} for
                label, value in
                zip(out['labels'], out['dataset'])]

        return list(query.rotating_colors(out))

    @classmethod
    def async_resolve_all(cls, instances):
        for instance in instances:
            if instance.async_query:
                continue
            instance._process()
        results = query.query_async_resolve([x.async_query for x in instances])
        for result, instance in zip(results, instances):
            instance.res = result


class Interval(object):
    def __init__(self, data):
        self.start = self._parse_date(data['interval']['start'])
        self.end = self._parse_date(data['interval']['end'])

        if 'results' not in data or not data['results']:
            self.payload = []
        elif not isinstance(data['results'], list):
            self.payload = [data['results']]
        else:
            self.payload = data['results']

    def _parse_date(self, date):
        # We need to strip off the timezone because the times are always
        # returned in the correct timezone for the user. Python has issues
        # with parsing basically anything.

        # 2015-07-06T00:00:00+00:00
        stripped = TIMZONE_KILLA.match(date).group(1)
        # 2015-07-06T00:00:00
        return datetime.datetime.strptime(stripped, '%Y-%m-%dT%H:%M:%S')
