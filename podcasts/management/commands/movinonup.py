from __future__ import absolute_import

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from accounts.models import Network
from podcasts.models import Podcast, PodcastEpisode
from sites.models import Site


class Command(BaseCommand):
    help = 'Update asset URLs to point at the new pinecast-storage repo'

    def add_arguments(self, parser):
        parser.add_argument('--bucket',
            action='store',
            dest='bucket',
            help='The bucket name to migrate')
        parser.add_argument('--run',
            action='store_true',
            dest='run',
            default=False,
            help='Actually runs the command instead of doing a dry run')

    def handle(self, *args, **options):
        self.options = options
        self.bucket_bare = '//%s.s3.amazonaws.com/' % self.options['bucket']
        self.correct_bucket_bare = '//%s.s3.amazonaws.com/' % settings.S3_BUCKET
        self.http_bucket = 'http://%s.s3.amazonaws.com/' % self.options['bucket']
        self.https_bucket = 'https://%s.s3.amazonaws.com/' % self.options['bucket']

        self.update_network_covers()
        self.update_podcast_images()
        self.update_episode_audio()
        self.update_episode_images()
        self.update_site_covers()
        self.update_site_logos()

        self.stdout.write('Completed')
        if not options['run']:
            self.stdout.write('Nothing was changed. Use --run to actually migrate')

    def update_network_covers(self):
        self.stdout.write('Inspecting network cover art...')

        instances = Network.objects.filter(
            Q(image_url__startswith=self.http_bucket) |
            Q(image_url__startswith=self.https_bucket))

        self.stdout.write('Found %d instances of network cover art' % instances.count())
        if self.options['run']:
            self.stdout.write('Updating %d instances...' % instances.count())
            for instance in instances:
                new_url = instance.image_url.replace(self.bucket_bare, self.correct_bucket_bare)
                self.stdout.write('    Updating %s to %s' % (instance.image_url, new_url))
                instance.image_url = new_url
                instance.save()
        else:
            self.stdout.write('Simulating updates to %d instances...' % instances.count())
            for instance in instances:
                new_url = instance.image_url.replace(self.bucket_bare, self.correct_bucket_bare)
                self.stdout.write('    Updating %s to %s' % (instance.image_url, new_url))

    def update_podcast_images(self):
        self.stdout.write('Inspecting podcast cover art...')

        instances = Podcast.objects.filter(
            Q(cover_image__startswith=self.http_bucket) |
            Q(cover_image__startswith=self.https_bucket))

        self.stdout.write('Found %d instances of podcast cover art' % instances.count())
        if self.options['run']:
            self.stdout.write('Updating %d instances...' % instances.count())
            for instance in instances:
                new_url = instance.cover_image.replace(self.bucket_bare, self.correct_bucket_bare)
                self.stdout.write('    Updating %s to %s' % (instance.cover_image, new_url))
                instance.cover_image = new_url
                instance.save()
        else:
            self.stdout.write('Simulating updates to %d instances...' % instances.count())
            for instance in instances:
                new_url = instance.cover_image.replace(self.bucket_bare, self.correct_bucket_bare)
                self.stdout.write('    Updating %s to %s' % (instance.cover_image, new_url))

    def update_episode_audio(self):
        self.stdout.write('Inspecting episode audio...')

        instances = PodcastEpisode.objects.filter(
            Q(audio_url__startswith=self.http_bucket) |
            Q(audio_url__startswith=self.https_bucket))

        self.stdout.write('Found %d instances of episode audio' % instances.count())
        if self.options['run']:
            self.stdout.write('Updating %d instances...' % instances.count())
            for instance in instances:
                new_url = instance.audio_url.replace(self.bucket_bare, self.correct_bucket_bare)
                self.stdout.write('    Updating %s to %s' % (instance.audio_url, new_url))
                instance.audio_url = new_url
                instance.save()
        else:
            self.stdout.write('Simulating updates to %d instances...' % instances.count())
            for instance in instances:
                new_url = instance.audio_url.replace(self.bucket_bare, self.correct_bucket_bare)
                self.stdout.write('    Updating %s to %s' % (instance.audio_url, new_url))

    def update_episode_images(self):
        self.stdout.write('Inspecting episode custom cover art...')

        instances = PodcastEpisode.objects.filter(
            Q(image_url__startswith=self.http_bucket) |
            Q(image_url__startswith=self.https_bucket))

        self.stdout.write('Found %d instances of episode cover art' % instances.count())
        if self.options['run']:
            self.stdout.write('Updating %d instances...' % instances.count())
            for instance in instances:
                new_url = instance.image_url.replace(self.bucket_bare, self.correct_bucket_bare)
                self.stdout.write('    Updating %s to %s' % (instance.image_url, new_url))
                instance.image_url = new_url
                instance.save()
        else:
            self.stdout.write('Simulating updates to %d instances...' % instances.count())
            for instance in instances:
                new_url = instance.image_url.replace(self.bucket_bare, self.correct_bucket_bare)
                self.stdout.write('    Updating %s to %s' % (instance.image_url, new_url))

    def update_site_covers(self):
        self.stdout.write('Inspecting site hero images...')

        instances = Site.objects.filter(
            Q(cover_image_url__startswith=self.http_bucket) |
            Q(cover_image_url__startswith=self.https_bucket))

        self.stdout.write('Found %d instances of hero images' % instances.count())
        if self.options['run']:
            self.stdout.write('Updating %d instances...' % instances.count())
            for instance in instances:
                new_url = instance.cover_image_url.replace(self.bucket_bare, self.correct_bucket_bare)
                self.stdout.write('    Updating %s to %s' % (instance.cover_image_url, new_url))
                instance.cover_image_url = new_url
                instance.save()
        else:
            self.stdout.write('Simulating updates to %d instances...' % instances.count())
            for instance in instances:
                new_url = instance.cover_image_url.replace(self.bucket_bare, self.correct_bucket_bare)
                self.stdout.write('    Updating %s to %s' % (instance.cover_image_url, new_url))

    def update_site_logos(self):
        self.stdout.write('Inspecting site logos...')

        instances = Site.objects.filter(
            Q(logo_url__startswith=self.http_bucket) |
            Q(logo_url__startswith=self.https_bucket))

        self.stdout.write('Found %d instances of site logos' % instances.count())
        if self.options['run']:
            self.stdout.write('Updating %d instances...' % instances.count())
            for instance in instances:
                new_url = instance.logo_url.replace(self.bucket_bare, self.correct_bucket_bare)
                self.stdout.write('    Updating %s to %s' % (instance.logo_url, new_url))
                instance.logo_url = new_url
                instance.save()
        else:
            self.stdout.write('Simulating updates to %d instances...' % instances.count())
            for instance in instances:
                new_url = instance.logo_url.replace(self.bucket_bare, self.correct_bucket_bare)
                self.stdout.write('    Updating %s to %s' % (instance.logo_url, new_url))
