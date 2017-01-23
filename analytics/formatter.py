import datetime
import re

from django.conf import settings
from django.utils.translation import ugettext, ugettext_lazy

from . import query
from .constants import influx_databases, USER_TIMEFRAMES
from .influx import escape, get_client, ident
from .util import country_code_map
from accounts.models import UserSettings
from pinecast.types import StringTypes


TIMZONE_KILLA = re.compile(r'(\d\d\d\d\-\d\d\-\d\dT\d\d:\d\d:\d\d)(Z|[+\-]\d\d:\d\d)')

DELTAS = {
    'minutely': datetime.timedelta(minutes=1),
    'hourly': datetime.timedelta(hours=1),
    'daily': datetime.timedelta(days=1),
    'weekly': datetime.timedelta(weeks=1),
    'monthly': datetime.timedelta(weeks=4),
    'quarterly': datetime.timedelta(weeks=4 * 3),
    'yearly': datetime.timedelta(weeks=52),
}
INTERVALS = {
    'minutely': 'time(1m, %dh)',
    'hourly': 'time(1h, %dh)',
    'daily': 'time(1d, %dh)',
    'weekly': 'time(1w, %dh)',
    'monthly': 'time(30d, %dh)',
    'quarterly': 'time(13w, %dh)',
    'yearly': 'time(365d, %dh)',
}

IGNORE_TZ_OFFSET = {
    'daily',
    'weekly',
    'monthly',
    'quarterly',
    'yearly',
}

dtnow = datetime.datetime.now

def select_format(k, v):
    if isinstance(v, bool) and v or v is None:
        return ident(k)

    if v == 'count':
        return 'COUNT(%s)' % ident(k)
    elif v == 'distinct':
        return 'DISTINCT(%s)' % ident(k)

    raise Exception('Unknown selector %s' % v)

def where_format(k, v):
    if isinstance(v, StringTypes):
        return '%s = %s' % (ident(k), escape(v))

    if isinstance(v, (list, tuple)):
        return '(%s)' % ' OR '.join(where_format(k, val) for val in v)

    raise Exception('Unknown clause type %s' % type(v))


def _parse_date(date):
    # We need to strip off the timezone because the times are always
    # returned in the correct timezone for the user. Python has issues
    # with parsing basically anything.

    # 2015-07-06T00:00:00+00:00
    stripped = TIMZONE_KILLA.match(date).group(1)
    # 2015-07-06T00:00:00
    return datetime.datetime.strptime(stripped, '%Y-%m-%dT%H:%M:%S')


class Format(object):
    def __init__(self, req, event_type):
        self.db = influx_databases[event_type]
        self.event_type = event_type
        self.req = req
        self.selection = {}
        self.criteria = {}
        self.timeframe = None
        self.force_timeframe = False
        self.interval_val = None
        self.group_by = None
        self.res = None

    def select(self, **kwargs):
        self.selection.update(kwargs)
        return self

    def where(self, **kwargs):
        self.criteria.update(kwargs)
        return self

    def group(self, by):
        self.group_by = by
        return self

    def during(self, timeframe=None, force=False, **kwargs):
        self.timeframe = timeframe or kwargs
        if force:
            self.force_timeframe = True
        return self

    def last_thirty(self, force=False):
        self.timeframe = 'month'
        if force:
            self.force_timeframe = True
        return self

    def interval(self, value=None):
        self.interval_val = value or self.req.GET.get('interval', 'daily')
        if self.interval_val not in DELTAS:
            self.interval_val = 'daily'
        return self

    def _process(self):
        assert self.selection

        select = ', '.join(
            select_format(k, v) for
            k, v in
            self.selection.items())
        where = ''
        group_by = ''

        tz = UserSettings.get_from_user(self.req.user).tz_offset

        if self.criteria:
            where = ' AND '.join(
                where_format(k, v) for
                k, v in
                self.criteria.items()
            )
        if self.group_by:
            if isinstance(self.group_by, (list, tuple)):
                group_by = ', '.join(ident(x) for x in self.group_by)
            else:
                group_by = ident(self.group_by)

        if self.timeframe:
            tf = USER_TIMEFRAMES.get(
                self.req.GET.get('timeframe', self.timeframe) if
                    not self.force_timeframe else
                    self.timeframe,
                lambda tz: None)(tz)
            if tf:
                if where:
                    where += ' AND '
                where += tf

        if self.interval_val:
            if group_by:
                group_by += ', '
            group_by += INTERVALS[self.interval_val] % (-1 * self._get_tz_offset().total_seconds() // 3600)

        query = 'SELECT %s FROM %s' % (select, ident(self.event_type))
        if where:
            query += ' WHERE %s' % where
        if group_by:
            query += ' GROUP BY %s' % group_by

        query += ';'

        if settings.DEBUG:
            print(query)

        self.res = get_client().query(query, database=self.db)

        return self

    def _get_keys(self):
        key = self.group_by[0] if isinstance(self.group_by, (list, tuple)) else self.group_by
        value_key = list(self.selection.items())[0][1]
        return key, value_key

    def _get_tz_offset(self):
        tz = UserSettings.get_from_user(self.req.user).tz_offset
        return datetime.timedelta(hours=tz)

    def _get_parsed_dates(self, points=None):
        if not points:
            points = list(self.res.items())[0][1]
        tz_offset = self._get_tz_offset()
        return (_parse_date(x['time']) + tz_offset for x in points)

    def _get_date_labels(self, points=None):
        interval_duration = DELTAS[self.interval_val]
        sformat = '%H:%M' if interval_duration < DELTAS['daily'] else '%x'
        return [x.strftime(sformat) for x in self._get_parsed_dates(points)]

    def format_country(self, label=ugettext_lazy('Series')):
        if not self.res: self._process()
        if not self.res: return []

        header = [[ugettext('Country Code'), ugettext('Country'), label]]
        key, value_key = self._get_keys()

        return header + [
            [tags[key], country_code_map[tags[key]], list(v)[0][value_key]] for
            (_, tags), v in
            self.res.items()
        ]

    def format_interval(self, field='count'):
        if not self.interval_val: self.interval()
        if not self.res: self._process()

        if not self.res:
            # TODO: come up with better error handling
            return {'labels': [''],
                    'datasets': [{'label': '', 'data': []}]}

        points = list(self.res.get_points())

        return {
            'labels': self._get_date_labels(points),
            'datasets': list(query.rotating_colors(
                [
                    {
                        'label': 'Series',
                        'data': [x[field] for x in points],
                        'pointStrokeColor': '#fff',
                    },
                ],
                key='strokeColor',
                highlight_key='pointColor',
            )),
        }

    def format_intervals(self, labels_map={}, extra_data={}):
        assert self.group_by

        if not self.interval_val: self.interval()
        if not self.res: self._process()

        if not self.res:
            # TODO: come up with better error handling
            return {'labels': [''],
                    'datasets': [{'label': '', 'data': []}]}

        key, value_key = self._get_keys()

        return {
            'labels': self._get_date_labels(),
            'datasets': list(query.rotating_colors(
                [
                    dict(
                        label=labels_map.get(tags[key], tags[key]),
                        data=[x[value_key] for x in v],
                        pointStrokeColor='#fff',
                        **extra_data.get(tags[key], {})
                    ) for
                    (_, tags), v in
                    self.res.items()
                ],
                key='strokeColor',
                highlight_key='pointColor',
            )),
        }

    def format_breakdown(self, groups=None):
        if not groups: groups = {}
        if not self.res: self._process()
        if not self.res: return []  # TODO: come up with better error handling

        key, value_key = self._get_keys()

        return list(query.rotating_colors(
            {
                'label': groups.get(tags[key], tags[key]),
                'value': list(v)[0][value_key],
            } for
            (_, tags), v in
            self.res.items()
        ))

    def get_resulting_value(self, field):
        if not self.res: self._process()
        if not self.res: return []

        return (x[field] for x in self.res.get_points())

    def get_resulting_values(self, fields):
        if not self.res: self._process()
        if not self.res: return []

        return (
            {f: x[v] for f, v in fields} for
            x in
            self.res.get_points())

    def get_resulting_groups(self):
        if not self.res: self._process()
        return [groupings[self.group_by] for _, groupings in self.res.keys()]
