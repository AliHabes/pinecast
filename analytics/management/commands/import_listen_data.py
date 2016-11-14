import datetime
import json
import re

from django.conf import settings
from django.core.management.base import BaseCommand

from analytics.log import get_listen_obj, commit_listens


TS_KILLA = re.compile(r'(\d\d\d\d\-\d\d\-\d\dT\d\d:\d\d:\d\d)(\..*)?Z')

class FakeReq(object):
    def __init__(self, ua, ip, country):
        self.__is_fake__ = True
        self.META = {
            'HTTP_USER_AGENT': ua,
            'HTTP_CF_CONNECTING_IP': ip,
            'HTTP_CF_IPCOUNTRY': country,
        }

class FakePod(object):
    def __init__(self, id_):
        self.id = id_

class FakeEp(object):
    def __init__(self, id_, pod_id):
        self.id = id_
        self.podcast = FakePod(pod_id)


class Command(BaseCommand):
    help = 'Import data to influxdb listen db from getconnect export'

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

        lobjs = []
        ignored = 0
        cache_hits = 0

        country_cache = {}

        with open(options.get('source')) as source:
            for i, line in enumerate(source):
                parsed = json.loads(line)

                was_unset = False
                try:
                    if not parsed['profile']['country'] and parsed['profile']['ip'] in country_cache:
                        parsed['profile']['country'] = country_cache[parsed['profile']['ip']]
                        cache_hits += 1
                    elif not parsed['profile']['country']:
                        was_unset = True
                        self.stdout.write('Country needs to be fetched...')

                    fake_req = FakeReq(
                        ua=parsed['profile']['ua'] or 'Unknown',
                        ip=parsed['profile']['ip'],
                        country=parsed['profile']['country'])

                    fake_ep = FakeEp(parsed['episode'], parsed['podcast'])
                    source = parsed['source']

                except Exception as e:
                    self.stderr.write('(%d): %s' % (i, str(e)))
                    continue

                try:
                    raw_ts = TS_KILLA.match(parsed['timestamp']).group(1)
                except Exception:
                    self.stderr.write('(%d): Failed to parse ts %s' % (i, parsed['timestamp']))
                    continue

                ts = datetime.datetime.strptime(raw_ts, '%Y-%m-%dT%H:%M:%S')

                result = get_listen_obj(fake_ep, source, fake_req, timestamp=ts)
                if not result:
                    ignored += 1
                    continue
                lobjs.append((None, result[1]))

                if was_unset:
                    country_cache[result[0]['profile']['ip']] = result[0]['profile']['country']

                if i % 500 == 0:
                    if ignored:
                        self.stdout.write('Ignored %d records so far' % ignored)
                    if cache_hits:
                        self.stdout.write('%d country cache hits' % cache_hits)

                    if not dry_run:
                        commit_listens(lobjs)
                    lobjs = []
                    self.stdout.write('Checkpoint: %d lines' % i)

        if dry_run:
            self.stdout.write('Dry run: no results were committed. Use --run to actually run')
        else:
            commit_listens(lobjs)

