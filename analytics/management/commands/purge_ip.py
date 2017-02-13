from __future__ import absolute_import

import datetime
import json
import re

from django.conf import settings
from django.core.management.base import BaseCommand

from analytics.influx import escape, get_client


class Command(BaseCommand):
    help = 'Remove listens from a specific IP address'

    def add_arguments(self, parser):
        parser.add_argument('--run',
            action='store_true',
            dest='run',
            default=False,
            help='Actually runs the command instead of doing a dry run')
        parser.add_argument('--ip',
            action='store',
            dest='ip',
            help='The IP address to purge')
        parser.add_argument('--podcast',
            action='store',
            dest='podcast',
            default=None,
            help='The podcast to limit the query to (optional)')
        parser.add_argument('--ua',
            action='store',
            dest='ua',
            default=None,
            help='The ua to limit the query to (optional)')

    def handle(self, *args, **options):
        dry_run = not options.get('run')
        if dry_run:
            self.stdout.write('DRY RUN')

        client = get_client()

        condition = '"ip" = %s' % escape(options.get('ip'))
        if options.get('podcast'):
            condition += ' AND "podcast" = %s' % escape(options.get('podcast'))
        if options.get('ua'):
            condition += ' AND "ua" = %s' % escape(options.get('ua'))

        query = 'SELECT v from "listen" WHERE %s;' % condition
        self.stdout.write(query)

        results = client.query(query, database=settings.INFLUXDB_DB_LISTEN)
        items = results.items()
        if not items:
            self.stdout.write('No matching points were found.')
            return

        timestamps = [x['time'] for x in items[0][1]]
        grouped_timestamps = [timestamps[i:i + 10] for i in range(0, len(timestamps), 10)]

        count = 0
        for ts in grouped_timestamps:
            count += 1
            queries = []
            for measurement in ('listen', 'listen-platform', 'listen-country'):
                queries.append('DELETE FROM "%s" WHERE %s' % (
                    measurement,
                    ' OR '.join('time = %s' % escape(x) for x in ts)))
            delete_query = '; '.join(queries)
            self.stdout.write(delete_query)
            if not dry_run:
                client.query(delete_query, database=settings.INFLUXDB_DB_LISTEN)

        self.stdout.write('Removed %d listens' % count)
        self.stdout.write('Removed %d points' % (count * 3))

        if dry_run:
            self.stdout.write('This was a dry run. Use --run to actually remove points.')
