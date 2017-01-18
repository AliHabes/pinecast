from __future__ import absolute_import

import datetime
import uuid

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import ugettext

from . import importer_worker
from podcasts.models import Podcast, PodcastEpisode


class AssetImportRequest(models.Model):
    created = models.DateTimeField(auto_now_add=True)

    podcast = models.ForeignKey(Podcast, null=True, blank=True)
    episode = models.ForeignKey(PodcastEpisode, null=True, blank=True)

    expiration = models.DateTimeField()
    audio_source_url = models.URLField(blank=True, max_length=500)
    image_source_url = models.URLField(blank=True, max_length=500)
    access_token = models.CharField(max_length=128)

    resolved = models.BooleanField(default=False)

    failed = models.BooleanField(default=False)
    failure_message = models.TextField(null=True, blank=True)

    @classmethod
    def create(cls, *args, **kwargs):
        if 'access_token' not in kwargs:
            kwargs['access_token'] = AssetImportRequest.get_token()
        return cls(*args, **kwargs)

    @classmethod
    def get_token(cls):
        return str(uuid.uuid4())

    def get_json_payload(self):
        return {
            'id': self.id,
            'item_type': 'image' if self.image_source_url else 'audio',
            'entity':
                {'id': str(self.episode.id), 'name': self.episode.title, 'type': 'episode'} if
                self.episode else
                {'id': str(self.podcast.id), 'name': self.podcast.name, 'type': 'podcast'},
            'entity_type': 'episode' if self.episode else 'podcast',
            'resolved': self.resolved,
            'failed': self.failed,
            'failure_message': self.failure_message,
        }

    def resolve(self, new_url):
        if self.resolved:
            raise Exception(ugettext('Attempting to double-resolve import request'))

        if self.expiration < datetime.datetime.now():
            raise Exception(ugettext('Attempting to resolve expired import request'))

        if self.podcast:
            if self.audio_source_url:
                raise Exception(ugettext('Invalid import request'))

            orig_url = self.podcast.cover_image
            self.podcast.cover_image = new_url
            self.podcast.save()

            eps = self.podcast.podcastepisode_set.filter(image_url=orig_url)
            for ep in eps:
                ep.image_url = new_url
                ep.save()

        elif self.episode:
            if self.audio_source_url:
                self.episode.audio_url = new_url
            else:
                self.episode.image_url = new_url

            if (settings.S3_BUCKET in self.episode.audio_url and
                settings.S3_BUCKET in self.episode.image_url):
                self.episode.awaiting_import = False
            self.episode.save()

        else:
            raise Exception(ugettext('Invalid import request for neither podcast nor ep'))

        self.resolved = True
        self.save()

    def get_payload(self):
        source = self.audio_source_url or self.image_source_url
        clean_source = source
        if '#' in clean_source:  # Strip off hashes
            clean_source = clean_source[:clean_source.index('#')]
        if '?' in clean_source:  # Strip off query params
            clean_source = clean_source[:clean_source.index('?')]

        if self.podcast:
            key = 'podcasts/covers/'
        else:
            key = 'podcasts/%s/%s/' % (
                str(self.episode.podcast.id),
                'image' if self.image_source_url else 'audio')
        key = '%s%s/%s' % (key, str(uuid.uuid4()), clean_source[clean_source.rindex('/') + 1:])

        pod = self.podcast or self.episode.podcast

        return {
            'type': 'import_asset',
            'token': self.access_token,
            'id': self.id,
            'url': source,
            'bucket': settings.S3_BUCKET,
            'key': key,
        }

    def trace_podcast(self):
        return self.podcast or self.episode.podcast

    def asset_type(self):
        return 'image' if self.image_source_url else 'audio'

    def status(self):
        if self.resolved:
            return 'resolved'
        elif self.failed:
            return 'failed'
        else:
            return 'unresolved'

    def __str__(self):
        return self.audio_source_url or self.image_source_url


class Collaborator(models.Model):
    created = models.DateTimeField(auto_now_add=True)

    podcast = models.ForeignKey(Podcast, null=True, blank=True, related_name='collaborators')
    collaborator = models.ForeignKey(User, related_name='collaborated_podcasts')

    def __str__(self):
        return '%s - %s' % (self.podcast.name, self.collaborator.email)
