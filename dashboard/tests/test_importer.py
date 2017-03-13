from nose.tools import eq_

from ..importer import _parse_duration


def test_parse_duration():
    eq_(_parse_duration('12'), 12)
    eq_(_parse_duration('012'), 12)
    eq_(_parse_duration('0:12'), 12)
    eq_(_parse_duration('1:12'), 72)
    eq_(_parse_duration('01:12'), 72)
    eq_(_parse_duration('0:01:12'), 72)
    eq_(_parse_duration('1:01:12'), 3672)
    eq_(_parse_duration('01:01:12'), 3672)

    eq_(_parse_duration('0::01:12'), 72)
    eq_(_parse_duration('0::01::12'), 72)
    eq_(_parse_duration('1::01::12'), 3672)
