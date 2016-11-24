from __future__ import absolute_import

from nose.tools import eq_

from ..jinja2_helper import safe_json


def test_safe_json():
    unsafe = '<"\'>'
    safe = '"&lt;&#34;&#39;&gt;"'
    eq_(str(safe_json(unsafe)), safe)
    eq_(str(safe_json(None)), 'null')
    eq_(str(safe_json(1)), '1')
    eq_(str(safe_json(1.5)), '1.5')
    # eq_(str(safe_json(long(100))), '100')
    eq_(str(safe_json(True)), 'true')
    eq_(str(safe_json(False)), 'false')

    eq_(str(safe_json([])), '[]')
    eq_(str(safe_json([1, 'foo'])), '[1,"foo"]')
    eq_(str(safe_json([1, ['foo', unsafe]])), '[1,["foo",%s]]' % safe)

    eq_(str(safe_json({'foo': 'bar'})), '{"foo":"bar"}')
    eq_(str(safe_json({'foo': {'zip': unsafe}})), '{"foo":{"zip":%s}}' % safe)
