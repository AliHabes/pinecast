# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division

import datetime
import json

import bleach
import gfm
import requests
import rollbar
from django.conf import settings
from django.db import models
from django.utils.translation import ugettext, ugettext_lazy

from pinecast.helpers import pretty_date, reverse
from pinecast.email import _send_mail as send_mail
from pinecast.constants import MILESTONES
from podcasts.models import Podcast, PodcastEpisode


epoch = datetime.datetime.utcfromtimestamp(0)


def _next_ms(listens):
    return next(x for x in MILESTONES if x > listens)


class NotificationHook(models.Model):
    DESTINATIONS = (
        ('webhook', ugettext_lazy('Webhook')),
        ('slack', ugettext_lazy('Slack')),
        ('email', ugettext_lazy('Email')),
    )
    TRIGGERS = (
        ('tip', ugettext_lazy('On Tip')),
        ('feedback', ugettext_lazy('On Feedback')),
        ('first_listen', ugettext_lazy('On Episode First Listen')),
        ('listen_threshold', ugettext_lazy('On Episode Hit Listen Threshold')),
        ('growth_milestone', ugettext_lazy('On Hit Growth Milestone')),
    )

    podcast = models.ForeignKey(Podcast, related_name='notifications')

    destination_type = models.CharField(choices=DESTINATIONS, max_length=32)
    destination = models.CharField(max_length=512)
    trigger = models.CharField(choices=TRIGGERS, max_length=32)
    condition = models.CharField(blank=True, null=True, max_length=64)

    @classmethod
    def trigger_notification(cls, podcast, trigger_type, data={}):
        hooks = list(cls.objects.filter(podcast=podcast, trigger=trigger_type))
        if not hooks:
            return

        for hook in hooks:
            hook.execute(data)

    def test_condition(self, precondition, postcondition):
        if self.trigger == 'listen_threshold':
            cond = int(self.condition)
            if precondition >= cond or postcondition < cond:
                return False
        elif self.trigger == 'growth_milestone':
            return _next_ms(precondition) != _next_ms(postcondition)

        return True

    def send_test(self):
        class FakeEpisode(object):
            id = '1234-5678-90'
            title = 'Test Episode'
            subtitle = 'This is the episode subtitle'
            publish = datetime.datetime.now()
            description = 'This is the episode description. 😜'
            explicit_override = self.podcast.is_explicit
            podcast = self.podcast

        data = {}
        if self.trigger == 'tip':
            data.update(tipper='test-tipper@pinecast.com', amount=500)
        elif self.trigger == 'feedback':
            data.update(
                episode=FakeEpisode(),
                content='This is the body of the feedback',
                sender='test-sender@pinecast.com')
        elif self.trigger == 'first_listen':
            data.update(episode=FakeEpisode())
        elif self.trigger == 'listen_threshold':
            data.update(episode=FakeEpisode(), listens=int(self.condition) + 1)
        elif self.trigger == 'growth_milestone':
            data.update(before_listens=999, listens=1234)
        self.execute(data)

    def execute(self, data):
        failed = False
        def run():
            if self.destination_type == 'webhook':
                self._exec_webhook(data)
            elif self.destination_type == 'slack':
                self._exec_slack(data)
            elif self.destination_type == 'email':
                self._exec_email(data)

        if settings.DEBUG:
            run()
        else:
            try:
                run()
            except Exception as e:
                rollbar.report_message('Error sending notification: %s' % str(e), 'error')
                failed = True

        if settings.DEBUG:
            print('Attempted to send %s webhook by %s (failed: %s)' % (
                self.trigger, self.destination_type, failed))
        from analytics.log import write_notification
        write_notification(self, failed, data.get('test', False))


    def _exec_webhook(self, data):
        body = {
            'summary': self.get_summary(data),
            'link': self.get_link(data),
            'podcast': {
                'name': self.podcast.name,
                'slug': self.podcast.slug,
                'url': reverse('podcast_dashboard', podcast_slug=self.podcast.slug),
                'feed_url': reverse('feed', podcast_slug=self.podcast.slug),
            },
            'type': self.trigger,
        }

        def get_ep_obj():
            id_ = str(data['episode'].id)
            return {
                'id': id_,
                'title': data['episode'].title,
                'url': reverse('podcast_episode',
                               podcast_slug=self.podcast.slug,
                               episode_id=id_),
                'listen_url': reverse('listen', episode_id=id_),
                'player_url': reverse('player', episode_id=id_),
                'publish': data['episode'].publish.isoformat(),
            }

        if self.trigger == 'tip':
            body.update(tipper=data['tipper'], amount=data['amount'])
        elif self.trigger == 'feedback':
            body.update(content=data['content'])
            if data.get('episode'):
                body.update(episode=get_ep_obj())
        elif self.trigger == 'first_listen':
            body.update(episode=get_ep_obj())
        elif self.trigger == 'listen_threshold':
            body.update(episode=get_ep_obj(), threshold=int(self.condition))
        elif self.trigger == 'growth_milestone':
            body.update(
                listens=int(data['listens']),
                milestone=_next_ms(data['before_listens']))

        requests.post(
            self.destination,
            timeout=5,
            json=body)

    def _exec_slack(self, data):
        requests.post(
            self.destination,
            timeout=5,
            json={
                'attachments': [
                    x for x in
                    [
                        {
                            'fallback': self.get_summary(data),
                            'title': self.podcast.name,
                            'title_link': self.get_link(data),
                            'text': self.get_summary(data, tagged=False),
                            'footer': 'Pinecast Notifications',
                            # TODO: use the static URL builder thing
                            'footer_icon': 'https://pinecast.com/static/img/16x16.png',
                            'ts': (datetime.datetime.now() - epoch).total_seconds(),
                            'fields': self._get_slack_fields(data),
                        },
                        self._get_slack_episode(data),
                    ] if x
                ],
            })

    def _exec_email(self, data):
        summary = self.get_summary(data)
        link = self.get_link(data)
        podcast_link = reverse(
            'podcast_dashboard', podcast_slug=self.podcast.slug)
        body = ugettext(
            '%s\n\n'
            'This is an automated notification from Pinecast. It was configured '
            'for %s. To change this configuration, and disable these '
            'notifications, visit the dashboard at:\n\n'
            'https://pinecast.com%s#settings,notifications'
            '\n\nIf you do not have control over this Pinecast account, please '
            'contact us at support@pinecast.zendesk.com.\n\n'
            '- Pinecast\nhttps://pinecast.com') % (
                link, self.podcast.name, podcast_link)
        send_mail(
            to=self.destination,
            subject=summary,
            body=body)

    def get_link(self, data):
        link = reverse('podcast_dashboard', podcast_slug=self.podcast.slug)
        if self.trigger == 'feedback':
            if data.get('episode'):
                link = reverse(
                    'podcast_episode',
                    podcast_slug=self.podcast.slug,
                    episode_id=str(data['episode'].id)) + '#feedback'
            else:
                link += '#feedback'
        elif self.trigger == 'tip':
            link += '#tips'

        return 'https://pinecast.com' + link

    def get_summary(self, data, tagged=True):
        if self.trigger == 'tip':
            out = ugettext('Tip of $%.2f from %s') % (
                float(data['amount']) / 100, data['tipper'])
        elif self.trigger == 'feedback':
            if data.get('episode'):
                out = ugettext('Feedback on %s') % (
                    data['episode'].title)
            else:
                out = ugettext('Feedback was received')
        elif self.trigger == 'first_listen':
            out = ugettext('First listen on %s') % data['episode'].title
        elif self.trigger == 'listen_threshold':
            out = ugettext('Crossed listen threshold (%s) on %s') % (
                self.condition, data['episode'].title)
        elif self.trigger == 'growth_milestone':
            out = ugettext('Crossed growth milestone (%s)') % _next_ms(data['before_listens'])

        return '[%s] %s' % (self.podcast.name, out) if tagged else out

    def _get_slack_episode(self, data):
        ep = data.get('episode')
        if not ep:
            return None

        return {
            'fallback': ep.title,
            'title': ep.title,
            'title_link': 'https://pinecast.com' + reverse(
                'podcast_episode',
                podcast_slug=self.podcast.slug,
                episode_id=str(ep.id)),
            'text': self.get_episode_text(data),
            'fields': [
                {'title': 'Published', 'value': pretty_date(ep.publish), 'short': True},
                {
                    'title': 'Explicit',
                    'value':
                        'Yes' if (self.podcast.is_explicit if
                                  ep.explicit_override == PodcastEpisode.EXPLICIT_OVERRIDE_CHOICE_NONE else
                                  ep.explicit_override == PodcastEpisode.EXPLICIT_OVERRIDE_CHOICE_EXPLICIT) else
                        'No',
                    'short': True,
                },
            ],
        }

    def _get_slack_fields(self, data):
        if self.trigger == 'feedback':
            return [
                {'title': 'Message', 'value': data['content']},
                {'title': 'Sender', 'value': data['sender']},
            ]
        elif self.trigger == 'tip':
            return [
                {'title': 'Amount', 'value': '$%.2f' % (float(data['amount']) / 100), 'short': True},
                {'title': 'Tipper', 'value': data['tipper'], 'short': True},
            ]
        elif self.trigger == 'listen_threshold':
            return [
                {'title': 'Threshold', 'value': self.condition, 'short': True},
                {'title': 'Listen Count', 'value': data['listens'], 'short': True},
            ]
        elif self.trigger == 'growth_milestone':
            return [
                {'title': 'Milestone', 'value': _next_ms(data['before_listens']), 'short': True},
                {'title': 'Listen Count', 'value': data['listens'], 'short': True},
            ]
        return None

    def get_episode_text(self, data):
        ep = data['episode']
        if ep.subtitle:
            return ep.subtitle

        return bleach.clean(
            gfm.markdown(ep.description),
            tags=[],
            strip=True,
            strip_comments=True)[:140]

    def get_trigger_text(self):
        if self.trigger == 'listen_threshold':
            return ugettext('Episode receives %s listen(s)') % self.condition
        else:
            trigger_map = dict(NotificationHook.TRIGGERS)
            return trigger_map[self.trigger]

    def get_destination_text(self):
        return dict(NotificationHook.DESTINATIONS)[self.destination_type]

    def __unicode__(self):
        return '[%s] %s (%s)' % (self.podcast.name, self.trigger, self.destination_type)
