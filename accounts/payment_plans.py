from django.utils.translation import ugettext_lazy


PLAN_DEMO = 0
PLAN_STARTER = 1
PLAN_PRO = 2
PLAN_ULTIMATE = 3
PLAN_COMMUNITY = 4

PLANS = (
    (PLAN_DEMO, ugettext_lazy('Demo')),
    (PLAN_STARTER, ugettext_lazy('Starter')),
    (PLAN_PRO, ugettext_lazy('Pro')),
    (PLAN_ULTIMATE, ugettext_lazy('Ultimate')),
    (PLAN_COMMUNITY, ugettext_lazy('Community')),
)
PLANS_MAP = {x: y for x, y in PLANS}

PLAN_RANKS = {
    PLAN_DEMO: 0,
    PLAN_STARTER: 1,
    PLAN_COMMUNITY: 1,
    PLAN_PRO: 2,
    PLAN_ULTIMATE: 3,
}

FEATURE_MIN_COMMENT_BOX = PLAN_PRO
FEATURE_MIN_GEOANALYTICS = PLAN_PRO
FEATURE_MIN_GEOANALYTICS_EP = PLAN_PRO
FEATURE_MIN_IMPORTER = PLAN_STARTER
FEATURE_MIN_NETWORK = PLAN_PRO
FEATURE_MIN_PLAYER = PLAN_STARTER
FEATURE_MIN_TORRENT = PLAN_STARTER
FEATURE_MIN_SITES = PLAN_STARTER
FEATURE_MIN_BLOG = PLAN_PRO

PLANS_RAW = {
    'PLAN_DEMO': PLAN_DEMO,
    'PLAN_STARTER': PLAN_STARTER,
    'PLAN_PRO': PLAN_PRO,
    'PLAN_ULTIMATE': PLAN_ULTIMATE,
    'PLAN_COMMUNITY': PLAN_COMMUNITY,

    'FEATURE_MIN_COMMENT_BOX': FEATURE_MIN_COMMENT_BOX,
    'FEATURE_MIN_GEOANALYTICS': FEATURE_MIN_GEOANALYTICS,
    'FEATURE_MIN_GEOANALYTICS_EP': FEATURE_MIN_GEOANALYTICS_EP,
    'FEATURE_MIN_IMPORTER': FEATURE_MIN_IMPORTER,
    'FEATURE_MIN_NETWORK': FEATURE_MIN_NETWORK,
    'FEATURE_MIN_PLAYER': FEATURE_MIN_PLAYER,
    'FEATURE_MIN_TORRENT': FEATURE_MIN_TORRENT,
    'FEATURE_MIN_SITES': FEATURE_MIN_SITES,
    'FEATURE_MIN_BLOG': FEATURE_MIN_BLOG,
}

STRIPE_PLANS = {
    PLAN_STARTER: 'starter',
    PLAN_PRO: 'pro',
    PLAN_ULTIMATE: 'ultimate',
}


_MB = 1024 * 1024
MAX_FILE_SIZE = {
    PLAN_DEMO: 48 * _MB,
    PLAN_STARTER: 64 * _MB,
    PLAN_COMMUNITY: 64 * _MB,
    PLAN_PRO: 256 * _MB,
    PLAN_ULTIMATE: 256 * _MB,
}

PLAN_PODCAST_LIMITS = {
    PLAN_DEMO: 3,
    PLAN_COMMUNITY: 5,
}

PLAN_TIP_LIMITS = {
    # in cents
    PLAN_DEMO: 1500,
    PLAN_STARTER: 2000,
    PLAN_COMMUNITY: 5000,
    PLAN_PRO: 5000,
    PLAN_ULTIMATE: 10000,
}


def minimum(plan_to_compare, minimum_plan):
    return PLAN_RANKS[plan_to_compare] >= PLAN_RANKS[minimum_plan]

def has_reached_podcast_limit(user_settings):
    plan = user_settings.plan
    if plan not in PLAN_PODCAST_LIMITS:
        return False

    pod_count = user_settings.user.podcast_set.count()
    limit = max(PLAN_PODCAST_LIMITS[plan], user_settings.plan_podcast_limit_override)
    return pod_count >= limit
