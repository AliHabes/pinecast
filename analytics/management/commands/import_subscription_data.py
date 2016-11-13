import datetime
import json
import re

from django.conf import settings
from django.core.management.base import BaseCommand

from analytics.log import write_subscription


TS_KILLA = re.compile(r'(\d\d\d\d\-\d\d\-\d\dT\d\d:\d\d:\d\d)(\..*)?Z')

class FakeReq(object):
    def __init__(self, ua, ip, country):
        self.__is_fake__ = True
        self.META = {
            'HTTP_USER_AGENT': ua,
            'HTTP_CF_CONNECTING_IP': ip,
            'HTTP_CF_IPCOUNTRY': country,
        }

class Command(BaseCommand):
    help = 'Re-run log aggregator against archived log files'

    def add_arguments(self, parser):
        parser.add_argument('--run',
            action='store_true',
            dest='run',
            default=False,
            help='Actually runs the command instead of doing a dry run')
        parser.add_argument('--source',
            action='store',
            dest='source',
            help='The path to the source JSON file')

    def handle(self, *args, **options):
        dry_run = not options.get('run')
        if not dry_run and not settings.DISABLE_GETCONNECT:
            self.stderr.write('Refusing to do a live run with DISABLE_GETCONNECT set to false')
            return
        elif dry_run:
            self.stdout.write('DRY RUN')

        with open(options.get('source')) as source:
            for i, line in enumerate(source):
                parsed = json.loads(line)
                try:
                    fake_req = FakeReq(
                        ua=parsed['profile']['ua'] or 'Unknown',
                        ip=parsed['profile']['ip'],
                        country=parsed['profile']['country'])
                    podcast = parsed['podcast']
                except Exception as e:
                    self.stderr.write('(%d): %s' % (i, str(e)))
                    continue

                try:
                    raw_ts = TS_KILLA.match(parsed['timestamp']).group(1)
                except Exception:
                    self.stderr.write('(%d): Failed to parse ts %s' % (i, parsed['timestamp']))

                ts = datetime.datetime.combine(
                    datetime.datetime.strptime(raw_ts, '%Y-%m-%dT%H:%M:%S').date(),
                    datetime.time.min)

                write_subscription(fake_req, podcast, ts=ts, dry_run=dry_run)

                if i % 500 == 0:
                    self.stdout.write('Progress: %d lines' % i)

        if dry_run:
            self.stdout.write('Dry run: no results were committed. Use --run to actually run')

