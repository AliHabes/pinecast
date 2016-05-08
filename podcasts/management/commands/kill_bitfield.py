from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from podcasts.models import PodcastEpisode


class Command(BaseCommand):
    help = 'Migrates from django-bitfield to booleanfield instead'

    def add_arguments(self, parser):
        parser.add_argument('--run',
            action='store_true',
            dest='run',
            default=False,
            help='Actually runs the command instead of doing a dry run')

    def handle(self, *args, **options):
        count = 0
        for episode in PodcastEpisode.objects.iterator():
            episode.flair_feedback = episode.description_flair.feedback_link
            episode.flair_site_link = episode.description_flair.site_link
            episode.flair_powered_by = episode.description_flair.powered_by

            if options['run']:
                episode.save()

            count += 1

        self.stdout.write('%d episodes iterated' % count)
        if not options['run']:
            self.stdout.write('No episodes were updated. Use --run to actually apply')
