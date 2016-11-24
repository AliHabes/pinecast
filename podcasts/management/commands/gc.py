from __future__ import absolute_import

from boto3.session import Session
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from accounts.models import Network
from podcasts.models import Podcast, PodcastEpisode
from sites.models import Site


class Command(BaseCommand):
    help = 'Removes unreferenced files from the S3 bucket'

    def add_arguments(self, parser):
        parser.add_argument('--run',
            action='store_true',
            dest='run',
            default=False,
            help='Actually runs the command instead of doing a dry run')

    def handle(self, *args, **options):
        session = Session(aws_access_key_id=settings.S3_ACCESS_ID,
                          aws_secret_access_key=settings.S3_SECRET_KEY)
        res = session.resource('s3')

        self.to_delete = []

        self.clean_bucket(res, settings.S3_BUCKET, options)
        self.clean_bucket(res, settings.S3_PREMIUM_BUCKET, options)

        self.stdout.write('Completed analysis')
        self.stdout.write('%d files to remove' % len(self.to_delete))
        if options['run']:
            for f in self.to_delete:
                f.delete()
            self.stdout.write('Completed removal')
        else:
            self.stdout.write('No files were removed. Use --run to actually GC')

    def clean_bucket(self, res, bucket_name, options):
        self.stdout.write('Processing bucket: %s' % bucket_name)
        self.stdout.write('Downloading S3 manifest...')

        self.stdout.write('Analyzing bucket contents...')
        bucket = res.Bucket(bucket_name)
        for f in bucket.objects.all():
            canon_url = 'http://%s.s3.amazonaws.com/%s' % (bucket_name, f.key)
            https_canon_url = 'https://%s.s3.amazonaws.com/%s' % (bucket_name, f.key)
            self.stdout.write(' - %s' % canon_url)

            if (f.key.startswith('networks/covers/') and
                Network.objects.filter(
                    Q(image_url=canon_url) | Q(image_url=https_canon_url)).count()):
                self.stdout.write('     Still in use by Network')
                continue

            elif (f.key.startswith('podcasts/covers/') and
                Podcast.objects.filter(
                    Q(cover_image=canon_url) | Q(cover_image=https_canon_url)).count()):
                self.stdout.write('     Still in use by Podcast')
                continue

            if PodcastEpisode.objects.filter(Q(audio_url=canon_url) |
                                             Q(image_url=canon_url) |
                                             Q(audio_url=https_canon_url) |
                                             Q(image_url=https_canon_url)).count():
                self.stdout.write('     Still in use by PodcastEpisode')
                continue

            if Site.objects.filter(
                    Q(cover_image_url=canon_url) | Q(cover_image_url=https_canon_url) |
                    Q(logo_url=canon_url) | Q(logo_url=https_canon_url)).count():
                self.stdout.write('     Still in use by Site')
                continue

            self.to_delete.append(f)
