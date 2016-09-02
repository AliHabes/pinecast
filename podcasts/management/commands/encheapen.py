import datetime
import re

from boto3.session import Session
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from podcasts.models import Podcast, PodcastEpisode


class Command(BaseCommand):
    help = 'Moves content to S3 IA storage'

    def add_arguments(self, parser):
        parser.add_argument('--run',
            action='store_true',
            dest='run',
            default=False,
            help='Actually runs the command instead of doing a dry run')

    def handle(self, *args, **options):
        self.candidates_for_ia = []

        bucket_regexp = re.compile(r'//([\w\-]+)\.s3\.', re.I)
        key_regexp = re.compile(r'\.s3\.amazonaws\.com/(.+)', re.I)

        cutoff = datetime.datetime.now() - datetime.timedelta(days=30)
        for ep in PodcastEpisode.objects.filter(created__lt=cutoff,
                                                publish__lt=cutoff,
                                                awaiting_import=False):

            bucket_match = bucket_regexp.search(ep.audio_url)
            if not bucket_match:
                continue
            key_match = key_regexp.search(ep.audio_url)
            self.candidates_for_ia.append((bucket_match.group(1), key_match.group(1)))

        self.stdout.write('%d files possible to move' % len(self.candidates_for_ia))

        self.to_make_ia = []

        session = Session(aws_access_key_id=settings.S3_ACCESS_ID,
                          aws_secret_access_key=settings.S3_SECRET_KEY)
        res = session.resource('s3')

        for bucket, key in self.candidates_for_ia:
            try:
                obj = res.Object(bucket, key)
                data = obj.get()
                if data.get('StorageClass', 'STANDARD') == 'STANDARD':
                    self.to_make_ia.append(obj)
            except Exception as e:
                self.stdout.write('Could not locate %s in %s' % (key, bucket))
                self.stderr.write(str(e))
                continue

        self.stdout.write('%d files to be migrated' % len(self.to_make_ia))

        if options['run']:
            for obj in self.to_make_ia:
                try:
                    obj.put(StorageClass='STANDARD_IA')
                except Exception as e:
                    self.stdout.write('Could not update %s' % obj.key)
                    self.stderr.write(str(e))
            self.stdout.write('Completed migration')
        else:
            self.stdout.write('No files were migrated. Use --run to actually migrate')
