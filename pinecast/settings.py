from __future__ import absolute_import
from __future__ import print_function

"""
Django settings for pinecast project.

Generated by 'django-admin startproject' using Django 1.8.2.

For more information on this file, see
https://docs.djangoproject.com/en/1.8/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.8/ref/settings/
"""

import logging
import os

import mimetypes


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.8/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET', 'p)r2w-c!m^znb%2ppj0rxp9uu$+$q928w#*$41y5(eu$friqqv')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'True') == 'True'
DEBUG_TOOLBAR = os.environ.get('DEBUG_TOOLBAR', 'False') == 'True'

if DEBUG:
    ALLOWED_HOSTS = ['*']
else:
    ALLOWED_HOSTS = ['pinecast.herokuapp.com', 'pinecast.com', 'pinecast.co', '.pinecast.co']

if os.environ.get('ADMIN_IP'):
    INTERNAL_IPS = [os.environ.get('ADMIN_IP')]
else:
    INTERNAL_IPS = []


if DEBUG_TOOLBAR:
    print('Loading Django Debug Toolbar')

mimetypes.add_type("image/svg+xml", ".svg", True)

# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',

    'whitenoise.runserver_nostatic',
    'django.contrib.staticfiles',

    'accounts',
    'analytics',
    'dashboard',
    'feedback',
    'notifications',
    'payments',
    'podcasts',
    'sites',
)
if DEBUG:
    INSTALLED_APPS = INSTALLED_APPS + ('django_nose', 'nplusone.ext.django', )
if DEBUG_TOOLBAR:
    INSTALLED_APPS = INSTALLED_APPS + ('debug_toolbar', )

MIDDLEWARE_CLASSES = (
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.security.SecurityMiddleware',

    'sites.middleware.subdomains.SubdomainMiddleware',
    'pinecast.middleware.hnredirect.HostnameRedirect',
    'pinecast.middleware.tsredirect.TrailingSlashRedirect',
)
if DEBUG:
    MIDDLEWARE_CLASSES = ('nplusone.ext.django.NPlusOneMiddleware', ) + MIDDLEWARE_CLASSES
if DEBUG_TOOLBAR:
    MIDDLEWARE_CLASSES = ('debug_toolbar.middleware.DebugToolbarMiddleware', ) + MIDDLEWARE_CLASSES

ROOT_URLCONF = 'pinecast.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.jinja2.Jinja2',
        'APP_DIRS': True,
        'DIRS': [
            os.path.join(BASE_DIR, 'templates', 'jinja2'),
        ],
        'OPTIONS': {
            'environment': 'pinecast.jinja2_helper.environment',
        },
    },
    # This is needed for the admin app
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

SILENCED_SYSTEM_CHECKS = ['urls.W002']

WSGI_APPLICATION = 'pinecast.wsgi.application'

ADMINS = [
    ('basta', 'mattbasta@gmail.com'),
]

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
            'propagate': True,
        },
    },
}

if DEBUG:
    TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'


# Database
# https://docs.djangoproject.com/en/1.8/ref/settings/#databases

DATABASES = {}
try:
    import dj_database_url
    prod_db = dj_database_url.config()
    assert prod_db, 'No DB config found...'
    print('Using prod database')
    DATABASES['default'] = prod_db
    DATABASES['default']['CONN_MAX_AGE'] = 500
except Exception:
    print('Using SQLite db')
    DATABASES['default'] = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
        'OPTIONS': {'timeout': 5},
    }


# Internationalization
# https://docs.djangoproject.com/en/1.8/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True
USE_L10N = True
USE_THOUSAND_SEPARATOR = True

USE_TZ = False


def show_debug_toolbar(req):
    if req.is_ajax():
        return False
    return (
        req.META.get('REMOTE_ADDR') in INTERNAL_IPS or
        req.META.get('HTTP_CF_CONNECTING_IP') in INTERNAL_IPS
    )


DEBUG_TOOLBAR_CONFIG = {
    'SHOW_TOOLBAR_CALLBACK': show_debug_toolbar,
}


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.8/howto/static-files/

STATIC_URL = '/static/'
STATICFILES_DIRS = STATIC_DIRS = (
    os.path.join(BASE_DIR, 'static'),
)
STATIC_ROOT = STATIC_DIRS[0] + 'root'

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'


S3_BUCKET = os.environ.get('S3_BUCKET')
S3_LOGS_BUCKET = os.environ.get('S3_LOGS_BUCKET')
S3_PREMIUM_BUCKET = os.environ.get('S3_PREMIUM_BUCKET')
CDN_HOSTNAME = os.environ.get('CDN_HOSTNAME')
S3_ACCESS_ID = os.environ.get('S3_ACCESS_ID')
S3_SECRET_KEY = os.environ.get('S3_SECRET_KEY')
SQS_ACCESS_ID = os.environ.get('SQS_ACCESS_ID')
SQS_SECRET_KEY = os.environ.get('SQS_SECRET_KEY')
SES_ACCESS_ID = os.environ.get('SES_ACCESS_ID')
SES_SECRET_KEY = os.environ.get('SES_SECRET_KEY')

SQS_IMPORT_QUEUE = 'import_work'
SNS_IMPORT_BUS = 'arn:aws:sns:us-east-1:575938143306:import_notify'

RECAPTCHA_KEY = os.environ.get('RECAPTCHA_KEY')
RECAPTCHA_SECRET = os.environ.get('RECAPTCHA_SECRET')

STRIPE_API_KEY = os.environ.get('STRIPE_API_KEY')
STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY')

LAMBDA_ACCESS_SECRET = os.environ.get('LAMBDA_ACCESS_SECRET')
RSS_FETCH_ENDPOINT = os.environ.get('RSS_FETCH_ENDPOINT')

DEPLOY_SLACKBOT_URL = os.environ.get('DEPLOY_SLACKBOT_URL')

CANNY_SSO_KEY = os.environ.get('CANNY_SSO_KEY')

MAX_FILE_SIZE = 1024 * 1024 * 256
EMAIL_CONFIRMATION_MAX_AGE = 3600 * 24 * 2  # Two days

SUPPORT_URL = 'https://pinecast.zendesk.com'
SUPPORT_EMAIL = 'support@pinecast.zendesk.com'
SENDER_EMAIL = 'Matt@pinecast.com'


INFLUXDB_USERNAME = os.environ.get('INFLUXDB_USERNAME')
INFLUXDB_PASSWORD = os.environ.get('INFLUXDB_PASSWORD')
INFLUXDB_DB_SUBSCRIPTION = os.environ.get('INFLUXDB_DB_SUBSCRIPTION', 'subscription')
INFLUXDB_DB_LISTEN = os.environ.get('INFLUXDB_DB_SUBSCRIPTION', 'listen')
INFLUXDB_DB_NOTIFICATION = os.environ.get('INFLUXDB_DB_NOTIFICATION', 'notification')

ANALYTICS_PROVIDER = 'influx'


ROLLBAR = {
    'access_token': os.environ.get('ROLLBAR_ACCESS_TOKEN'),
    'environment': 'development' if DEBUG else 'production',
    'exception_level_filters': [
        ('django.http.Http404', 'ignored'),
    ],
    'branch': 'master',
    'root': os.getcwd(),
}

INFLUXDB_HOST = 'influx.service.pinecast.com'
INFLUXDB_PORT = 443
INFLUXDB_SSL = True

INFLUXDB_CONDITION_OVERRIDES = {}

DISABLE_GETCONNECT = True

CHALLENGE_URL = os.environ.get('CHALLENGE_URL')
CHALLENGE_RESPONSE = os.environ.get('CHALLENGE_RESPONSE')


REFERRAL_DISCOUNT = 40  # percent off
REFERRAL_DISCOUNT_DURATION = 4  # months

NPLUSONE_LOGGER = logging.getLogger('nplusone')
NPLUSONE_LOG_LEVEL = logging.ERROR


try:
    from .settings_local import *
except ImportError:
    pass


if not DEBUG:
    MIDDLEWARE_CLASSES = MIDDLEWARE_CLASSES + ('rollbar.contrib.django.middleware.RollbarNotifierMiddleware', )
