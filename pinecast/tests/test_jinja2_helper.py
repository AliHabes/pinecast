from datetime import datetime, timedelta

from nose.tools import eq_

from ..jinja2_helper import pretty_date


def test_pretty_date_future():
    eq_(pretty_date(datetime.utcnow() + timedelta(milliseconds=1)), 'imminently')
    eq_(pretty_date(datetime.utcnow() + timedelta(seconds=30)), '30 seconds from now')
    eq_(pretty_date(datetime.utcnow() + timedelta(minutes=1)), 'in a minute')
    eq_(pretty_date(datetime.utcnow() + timedelta(minutes=2)), '2 minutes from now')
    eq_(pretty_date(datetime.utcnow() + timedelta(hours=1)), 'in an hour')
    eq_(pretty_date(datetime.utcnow() + timedelta(hours=2)), '2 hours from now')
    eq_(pretty_date(datetime.utcnow() + timedelta(days=1)), 'tomorrow')
    eq_(pretty_date(datetime.utcnow() + timedelta(days=2)), '2 days from now')
    eq_(pretty_date(datetime.utcnow() + timedelta(days=7)), '1 week from now')
    eq_(pretty_date(datetime.utcnow() + timedelta(days=14)), '2 weeks from now')
    eq_(pretty_date(datetime.utcnow() + timedelta(days=60)), '2 months from now')
    eq_(pretty_date(datetime.utcnow() + timedelta(days=365)), '1 year from now')

def test_pretty_date_past():
    eq_(pretty_date(datetime.utcnow() - timedelta(milliseconds=1)), 'just now')
    eq_(pretty_date(datetime.utcnow() - timedelta(seconds=30)), '30 seconds ago')
    eq_(pretty_date(datetime.utcnow() - timedelta(minutes=1)), 'a minute ago')
    eq_(pretty_date(datetime.utcnow() - timedelta(minutes=2)), '2 minutes ago')
    eq_(pretty_date(datetime.utcnow() - timedelta(hours=1)), 'an hour ago')
    eq_(pretty_date(datetime.utcnow() - timedelta(hours=2)), '2 hours ago')
    eq_(pretty_date(datetime.utcnow() - timedelta(days=1)), 'yesterday')
    eq_(pretty_date(datetime.utcnow() - timedelta(days=2)), '2 days ago')
    eq_(pretty_date(datetime.utcnow() - timedelta(days=7)), '1 week ago')
    eq_(pretty_date(datetime.utcnow() - timedelta(days=14)), '2 weeks ago')
    eq_(pretty_date(datetime.utcnow() - timedelta(days=60)), '2 months ago')
    eq_(pretty_date(datetime.utcnow() - timedelta(days=365)), '1 year ago')
