from __future__ import absolute_import

import datetime
import re
import uuid
from datetime import timedelta

import gfm
import requests
from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.core.validators import URLValidator
from django.db import models
from django.utils.translation import ugettext, ugettext_lazy

import accounts.payment_plans as payment_plans
from accounts.models import Network, UserSettings
from pinecast.helpers import cached_method, reverse, round_now, sanitize


FLAIR_FEEDBACK = 'flair_feedback'
FLAIR_SITE_LINK = 'flair_site_link'
FLAIR_POWERED_BY = 'flair_powered_by'
FLAIR_TIP_JAR = 'flair_tip_jar'
FLAIR_REFERRAL_CODE = 'flair_referral_code'
FLAIR_FLAGS = (
    (FLAIR_FEEDBACK, ugettext_lazy('Feedback form link')),
    (FLAIR_SITE_LINK, ugettext_lazy('Link to podcast website')),
    (FLAIR_POWERED_BY, ugettext_lazy('Powered By Pinecast')),
    (FLAIR_TIP_JAR, ugettext_lazy('Tip Jar link')),
    (FLAIR_REFERRAL_CODE, ugettext_lazy('Pinecast referral code')),
)
FLAIR_FLAGS_MAP = {k: v for k, v in FLAIR_FLAGS}


class Podcast(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(unique=True)

    name = models.CharField(max_length=256)
    subtitle = models.CharField(max_length=512, default='', blank=True)

    created = models.DateTimeField(auto_now_add=True, editable=False)
    cover_image = models.URLField(max_length=500)
    description = models.TextField(blank=True)
    is_explicit = models.BooleanField(default=False)
    homepage = models.URLField(max_length=500, blank=True, validators=[URLValidator()])

    language = models.CharField(max_length=16, default='en-US')
    copyright = models.CharField(max_length=1024, blank=True)
    author_name = models.CharField(max_length=1024, default='Anonymous')

    owner = models.ForeignKey(User)

    rss_redirect = models.URLField(null=True, blank=True, max_length=500)
    stats_base_listens = models.PositiveIntegerField(default=0)

    networks = models.ManyToManyField(Network, blank=True)

    total_tips = models.PositiveIntegerField(
        default=0, help_text=ugettext_lazy(
            'Tips collected over podcast lifetime in cents'))

    private_after_nth = models.PositiveIntegerField(default=None, null=True, blank=True)
    private_after_age = models.PositiveIntegerField(
        default=None, null=True, blank=True,
        help_text=ugettext_lazy('Age in seconds'))
    private_access_min_subscription = models.PositiveIntegerField(
        default=None, null=True, blank=True,
        help_text=ugettext_lazy('Min sub value in cents'))

    @staticmethod
    def is_slug_valid(slug):
        return bool(re.match(r'^\w[\w-]*$', slug))

    @cached_method
    def get_site(self):
        try:
            return self.site
        except Exception:
            return None

    @cached_method
    def get_category_list(self):
        return ','.join(x.category for x in self.podcastcategory_set.all())

    def set_category_list(self, cat_str):
        existing = set(x.category for x in self.podcastcategory_set.all())
        new = set(cat_str.split(','))

        added = new - existing
        removed = existing - new

        for a in added:
            n = PodcastCategory(podcast=self, category=a)
            n.save()

        for r in removed:
            o = PodcastCategory.objects.get(podcast=self, category=r)
            o.delete()

    @cached_method
    def is_still_importing(self):
        return (self.assetimportrequest_set
            .filter(failed=False, resolved=False)
            .exists())

    @cached_method
    def get_all_episodes_raw(self):
        return PodcastEpisode.objects.filter(podcast=self)

    @cached_method
    def get_episodes(self, select_related=None, include_private=False):
        episodes = self.get_all_episodes_raw().filter(
            publish__lt=round_now(),
            awaiting_import=False).order_by('-publish')
        if not include_private:
            episodes = episodes.filter(is_private=False)
            if self.private_after_age is not None:
                max_age = round_now() - timedelta(seconds=self.private_after_age)
                episodes = episodes.filter(publish__gt=max_age)
            if self.private_after_nth is not None:
                episodes = episodes[:self.private_after_nth]

        if select_related:
            episodes = episodes.select_related(select_related)
        us = UserSettings.get_from_user(self.owner)
        if us.plan == payment_plans.PLAN_DEMO:
            episodes = episodes[:10]

        # This is a clever little optimization to prevent `episode.podcast`
        # from doing a db query, and avoiding needing to `select_related('podcast')`,
        # which also does extra work.
        for ep in episodes:
            setattr(ep, 'podcast', self)
        return episodes

    @cached_method
    def has_private_episodes(self):
        rn = round_now()
        episodes = self.get_all_episodes_raw().filter(
            publish__lt=rn,
            awaiting_import=False).order_by('-publish')

        if episodes.filter(is_private=True).exists():
            return True

        return (
            self.private_after_nth is not None and
                episodes.count() > self.private_after_nth or
            self.private_after_age is not None and
                episodes.filter(publish__lt=rn - timedelta(seconds=self.private_after_age)).exists()
        )

    @cached_method
    def get_unpublished_count(self):
        return self.podcastepisode_set.filter(
            publish__gt=round_now()).count()

    def get_available_flair_flags(self, flatten=False):
        us = UserSettings.get_from_user(self.owner)
        plan = us.plan
        flags = []
        if payment_plans.minimum(plan, payment_plans.PLAN_STARTER):
            # This is inside a conditional because it's forced on for free
            # users.
            flags.append(FLAIR_POWERED_BY)
        if payment_plans.minimum(plan, payment_plans.FEATURE_MIN_COMMENT_BOX):
            flags.append(FLAIR_FEEDBACK)
        if us.stripe_payout_managed_account:
            flags.append(FLAIR_TIP_JAR)

        if payment_plans.minimum(plan, payment_plans.FEATURE_MIN_SITES) and self.get_site():
            flags.append(FLAIR_SITE_LINK)

        if (plan != payment_plans.PLAN_DEMO and
            plan != payment_plans.PLAN_COMMUNITY and
            us.coupon_code):
            flags.append(FLAIR_REFERRAL_CODE)

        if flatten:
            return flags
        else:
            return [(f, FLAIR_FLAGS_MAP[f]) for f in flags]

    def __str__(self):
        return self.name

    def last_eligible_payout_date(self):
        today = datetime.date.today()
        days_since_friday = (today.isoweekday() - 5) % 7
        return today - timedelta(days=days_since_friday)


    def last_payout_date(self):
        last_eligible_payout_date = self.last_eligible_payout_date()

        last_day_for_charges_in_last_payout = (
            last_eligible_payout_date - timedelta(days=7))

        last_tip = (self.tip_events
            .filter(occurred_at__lte=last_day_for_charges_in_last_payout)
            .order_by('-occurred_at')
            .first())

        if not last_tip:
            return None

        return last_tip.payout_date()

    def next_payout_date(self):
        last_eligible_payout_date = self.last_eligible_payout_date()
        last_tip = (self.tip_events
                        .filter(occurred_at__gt=last_eligible_payout_date -
                                timedelta(days=7))
                        .order_by('-occurred_at')
                        .first())

        if not last_tip:
            return None

        return last_tip.payout_date()

    def average_tip_value_this_month(self):
        events = (self.tip_events
            .filter(occurred_at__gt=round_now() - timedelta(days=30)))
        return events.aggregate(models.aggregates.Avg('amount'))['amount__avg']

    def tip_fees_paid(self):
        return (self.tip_events.all()
                    .aggregate(
                        models.aggregates.Sum('fee_amount')))['fee_amount__sum'] or 0

    @cached_method
    def get_remaining_surge(self, max_size):
        uset = UserSettings.get_from_user(self.owner)
        if not payment_plans.minimum(uset.plan, payment_plans.PLAN_STARTER):
            return 0
        thirty_ago = datetime.datetime.now() - timedelta(days=30)
        last_thirty_eps = self.podcastepisode_set.filter(created__gt=thirty_ago, audio_size__gt=max_size)
        surge_count = last_thirty_eps.count()
        surge_amt = last_thirty_eps.aggregate(models.Sum('audio_size'))['audio_size__sum'] or 0
        surge_amt -= surge_count * max_size

        remaining = max_size - surge_amt
        return 0 if remaining < 0 else remaining


class PodcastEpisode(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    podcast = models.ForeignKey(Podcast)
    title = models.CharField(max_length=1024)
    subtitle = models.CharField(max_length=1024, default='', blank=True)
    created = models.DateTimeField(auto_now_add=True, editable=False)
    publish = models.DateTimeField(db_index=True)
    description = models.TextField(default='')
    duration = models.PositiveIntegerField(
        help_text=ugettext_lazy('Audio duration in seconds'))

    audio_url = models.URLField(max_length=500)
    audio_size = models.PositiveIntegerField(default=0)
    audio_type = models.CharField(max_length=64)

    image_url = models.URLField(max_length=500)

    copyright = models.CharField(max_length=1024, blank=True)
    license = models.CharField(max_length=1024, blank=True)

    awaiting_import = models.BooleanField(default=False)

    flair_feedback = models.BooleanField(default=False)
    flair_site_link = models.BooleanField(default=False)
    flair_powered_by = models.BooleanField(default=False)
    flair_tip_jar = models.BooleanField(default=False)
    flair_referral_code = models.BooleanField(default=False)

    EXPLICIT_OVERRIDE_CHOICE_NONE = 'none'
    EXPLICIT_OVERRIDE_CHOICE_EXPLICIT = 'expl'
    EXPLICIT_OVERRIDE_CHOICE_CLEAN = 'clen'
    explicit_override = models.CharField(
        max_length=4,
        choices=[
            (EXPLICIT_OVERRIDE_CHOICE_NONE, ugettext_lazy('None')),
            (EXPLICIT_OVERRIDE_CHOICE_EXPLICIT, ugettext_lazy('Explicit')),
            (EXPLICIT_OVERRIDE_CHOICE_CLEAN, ugettext_lazy('Clean')),
        ],
        default=EXPLICIT_OVERRIDE_CHOICE_NONE
    )

    stats_base_listens = models.PositiveIntegerField(default=0)

    # This is just an override. Use check_is_private() to determine if it is
    # private because of podcast-level settings.
    is_private = models.BooleanField(
        default=False, help_text=ugettext_lazy('Overrides other settings when true'))

    @cached_method
    def formatted_duration(self):
        seconds = self.duration
        return '%02d:%02d:%02d' % (
            seconds // 3600, seconds % 3600 // 60, seconds % 60)

    @cached_method
    def is_published(self):
        return not self.awaiting_import and self.publish <= round_now()

    @cached_method
    def check_is_private(self):
        if self.is_private:
            return True

        pod = self.podcast
        now = round_now()
        if (pod.private_after_age is not None and
            self.publish < now - timedelta(seconds=pod.private_after_age)):
            return True

        if pod.private_after_nth is not None:
            ep_count = (
                pod.get_all_episodes_raw()
                .filter(
                    publish__lt=now,
                    publish__gt=self.publish,
                    is_private=False,
                    awaiting_import=False)
                .count())
            if ep_count > pod.private_after_nth:
                return True

        return False

    def set_flair(self, post, no_save=False):
        for flag, _ in FLAIR_FLAGS:
            setattr(self, flag, bool(post.get('flair_%s' % flag)))
        if not no_save:
            self.save()

    def get_html_description(self, is_demo=None):
        raw = self.description
        us = UserSettings.get_from_user(self.podcast.owner)
        if is_demo is None:
            is_demo = us.plan == payment_plans.PLAN_DEMO
        available_flags = self.podcast.get_available_flair_flags(flatten=True)

        if (self.flair_tip_jar and
            FLAIR_TIP_JAR in available_flags):
            raw += '\n\nSupport %s by donating to the [tip jar](https://pinecast.com/payments/tips/%s).' % (
                self.podcast.name, self.podcast.slug)

        if self.flair_site_link and FLAIR_SITE_LINK in available_flags:
            site_url = self.podcast.get_site().get_domain()
            raw += '\n\nFind out more at [%s](%s).' % (self.podcast.name, site_url)

        if (self.flair_feedback and
            FLAIR_FEEDBACK in available_flags):
            prompt = self.get_feedback_prompt()
            fb_url = 'https://pinecast.com%s' % reverse(
                'ep_comment_box',
                podcast_slug=self.podcast.slug,
                episode_id=str(self.id))
            raw += '\n\n%s [%s](%s)' % (prompt, fb_url, fb_url)

        has_powered_by = is_demo or self.flair_powered_by and FLAIR_POWERED_BY in available_flags
        if has_powered_by:
            raw += ('\n\nThis podcast is powered by '
                    '[Pinecast](https://pinecast.com).')

        if self.flair_referral_code and FLAIR_REFERRAL_CODE in available_flags:
            if has_powered_by:
                raw += ' Try Pinecast for free, forever, no credit card required. '
            else:
                raw += (
                    '\n\nCheck out our podcasting host, '
                    '[Pinecast](https://pinecast.com). Start your own podcast '
                    'for free, no credit card required, forever. ')

            raw += (
                'If you decide to upgrade, use coupon code **%s** for %d%% off '
                'for %d months, and support %s.') % (
                    us.coupon_code,
                    settings.REFERRAL_DISCOUNT,
                    settings.REFERRAL_DISCOUNT_DURATION,
                    self.podcast.name)

        markdown = gfm.markdown(raw)
        return sanitize(markdown)

    def get_feedback_prompt(self, default=None):
        try:
            prompt = self.episodefeedbackprompt
            return prompt.prompt
        except ObjectDoesNotExist:
            return default if default is not None else ugettext(
                'Send us your feedback online:')

    def delete_feedback_prompt(self):
        try:
            self.episodefeedbackprompt.delete()
        except ObjectDoesNotExist:
            pass

    def get_url(self, source):
        return self.audio_url + '?x-source=%s&x-episode=%s' % (source, str(self.id))

    def __str__(self):
        return '%s - %s' % (self.title, self.subtitle)


CATEGORIES = set([
    'Arts',
    'Arts/Design',
    'Arts/Fashion & Beauty',
    'Arts/Food',
    'Arts/Literature',
    'Arts/Performing Arts',
    'Arts/Spoken Word',
    'Arts/Visual Arts',
    'Business',
    'Business/Business News',
    'Business/Careers',
    'Business/Investing',
    'Business/Management & Marketing',
    'Business/Shopping',
    'Comedy',
    'Education',
    'Education/Educational Technology',
    'Education/Higher Education',
    'Education/K-12',
    'Education/Language Courses',
    'Education/Training',
    'Games & Hobbies',
    'Games & Hobbies/Automotive',
    'Games & Hobbies/Aviation',
    'Games & Hobbies/Hobbies',
    'Games & Hobbies/Other Games',
    'Games & Hobbies/Video Games',
    'Government & Organizations',
    'Government & Organizations/Local',
    'Government & Organizations/National',
    'Government & Organizations/Non-Profit',
    'Government & Organizations/Regional',
    'Health',
    'Health/Alternative Health',
    'Health/Fitness & Nutrition',
    'Health/Self-Help',
    'Health/Sexuality',
    'Health/Kids & Family',
    'Music',
    'Music/Alternative',
    'Music/Blues',
    'Music/Country',
    'Music/Easy Listening',
    'Music/Electronic',
    'Music/Electronic/Acid House',
    'Music/Electronic/Ambient',
    'Music/Electronic/Big Beat',
    'Music/Electronic/Breakbeat',
    'Music/Electronic/Disco',
    'Music/Electronic/Downtempo',
    'Music/Electronic/Drum \'n\' Bass',
    'Music/Electronic/Garage',
    'Music/Electronic/Hard House',
    'Music/Electronic/House',
    'Music/Electronic/IDM',
    'Music/Electronic/Jungle',
    'Music/Electronic/Progressive',
    'Music/Electronic/Techno',
    'Music/Electronic/Trance',
    'Music/Electronic/Tribal',
    'Music/Electronic/Trip Hop',
    'Music/Folk',
    'Music/Freeform',
    'Music/Hip-Hop & Rap',
    'Music/Inspirational',
    'Music/Jazz',
    'Music/Latin',
    'Music/Metal',
    'Music/New Age',
    'Music/Oldies',
    'Music/Pop',
    'Music/R&B & Urban',
    'Music/Reggae',
    'Music/Rock',
    'Music/Seasonal & Holiday',
    'Music/Soundtracks',
    'Music/World',
    'News & Politics',
    'News & Politics/Conservative (Right)',
    'News & Politics/Liberal (Left)',
    'Religion & Spirituality',
    'Religion & Spirituality/Buddhism',
    'Religion & Spirituality/Christianity',
    'Religion & Spirituality/Hinduism',
    'Religion & Spirituality/Islam',
    'Religion & Spirituality/Judaism',
    'Religion & Spirituality/Other',
    'Religion & Spirituality/Spirituality',
    'Science & Medicine',
    'Science & Medicine/Medicine',
    'Science & Medicine/Natural Sciences',
    'Science & Medicine/Social Sciences',
    'Society & Culture',
    'Society & Culture/Gay & Lesbian',
    'Society & Culture/History',
    'Society & Culture/Personal Journals',
    'Society & Culture/Philosophy',
    'Society & Culture/Places & Travel',
    'Sports & Recreation',
    'Sports & Recreation/Amateur',
    'Sports & Recreation/College & High School',
    'Sports & Recreation/Outdoor',
    'Sports & Recreation/Professional',
    'TV & Film',
    'Technology',
    'Technology/Gadgets',
    'Technology/IT News',
    'Technology/Podcasting',
    'Technology/Software How-To',
])

class PodcastCategory(models.Model):
    category = models.CharField(max_length=128,
                                choices=[(x, x) for x in sorted(CATEGORIES)])
    podcast = models.ForeignKey(Podcast)

    def __str__(self):
        return '%s: %s' % (self.podcast.name, self.category)
