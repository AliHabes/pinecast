from __future__ import absolute_import

from django.db import models

from podcasts.models import Podcast, PodcastEpisode


class Feedback(models.Model):
    created = models.DateTimeField(auto_now_add=True)

    podcast = models.ForeignKey(Podcast)
    episode = models.ForeignKey(PodcastEpisode, null=True, blank=True)

    sender = models.EmailField()
    sender_ip = models.GenericIPAddressField(null=True)
    message = models.TextField()


class EpisodeFeedbackPrompt(models.Model):
    episode = models.OneToOneField(PodcastEpisode, primary_key=True)
    prompt = models.TextField()
