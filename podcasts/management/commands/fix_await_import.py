from __future__ import absolute_import

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from podcasts.models import PodcastEpisode


class Command(BaseCommand):
    help = 'Removes unreferenced files from the S3 bucket'

    def add_arguments(self, parser):
        parser.add_argument('--run',
            action='store_true',
            dest='run',
            default=False,
            help='Actually runs the command instead of doing a dry run')

    def handle(self, *args, **options):
        for episode in PodcastEpisode.objects.filter(awaiting_import=True):
            if episode.awaiting_import:
                self.stdout.write('Found episode: %s' % episode.title)
                if options['run']:
                    episode.awaiting_import = False
                    episode.save()
                    self.stdout.write('Fixed')

        if options['run']:
            self.stdout.write('Completed repair')
        else:
            self.stdout.write('No changes were made. To actually repair, use --run')
