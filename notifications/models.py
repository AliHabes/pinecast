import json

import requests
import rollbar
from django.conf import settings
from django.db import models
from django.utils.translation import ugettext, ugettext_lazy

from pinecast.helpers import reverse
from pinecast.email import _send_mail as send_mail
from pinecast.constants import MILESTONES
from podcasts.models import Podcast


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
            pre = next(x for x in MILESTONES if x > precondition)
            post = next(x for x in MILESTONES if x > postcondition)
            print pre, post
            return pre != post

        return True

    def execute(self, data):
        failed = False
        try:
            if self.destination_type == 'webhook':
                self._exec_webhook(data)
            elif self.destination_type == 'slack':
                self._exec_slack(data)
            elif self.destination_type == 'email':
                self._exec_email(data)
        except Exception as e:
            rollbar.report_message('Error sending notification: %s' % str(e), 'error')
            failed = True
            if settings.DEBUG:
                raise e
        finally:
            if settings.DEBUG:
                print 'Attempted to send %s webhook by %s (failed: %s)' % (
                    self.trigger, self.destination_type, failed)
            from analytics.log import write_notification
            write_notification(self, failed)


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
                'publish': data['episode'].publish.isoformat()
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
                episode=get_ep_obj(),
                listens=int(data['listens']),
                milestone=next(x for x in MILESTONES if x > data['before_listens']))

        requests.post(
            self.destination,
            timeout=5,
            json=body)

    def _exec_slack(self, data):
        requests.post(
            self.destination,
            timeout=5,
            json={
                'text': self.get_summary(data),
                'link': self.get_link(data)
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

    def get_summary(self, data):
        if self.trigger == 'tip':
            return ugettext('[%s] Tip of $%.2f from %s') % (
                self.podcast.name, float(data['amount']) / 100, data['tipper'])
        elif self.trigger == 'feedback':
            if data.get('episode'):
                return ugettext('[%s] Feedback on %s') % (
                    self.podcast.name, data['episode'].title)
            else:
                return ugettext('[%s] Feedback') % self.podcast.name
        elif self.trigger == 'first_listen':
            return ugettext('[%s] First listen on %s') % (
                self.podcast.name, data['episode'].title)
        elif self.trigger == 'listen_threshold':
            return ugettext('[%s] Crossed listen threshold (%s) on %s') % (
                self.podcast.name, self.condition, data['episode'].title)
        elif self.trigger == 'growth_milestone':
            return ugettext('[%s] Crossed growth milestone (%s)') % (
                self.podcast.name,
                next(x for x in MILESTONES if x > data['before_listens']))

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
