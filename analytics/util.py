from __future__ import absolute_import

from pinecast.types import StringTypes


def escape(val):
    if isinstance(val, StringTypes):
        return "'%s'" % val.replace("'", "\\'")
    elif isinstance(val, (int, float)):
        return str(val)

    raise Exception('Unknown type %s' % type(val))

def ident(val):
    return '"%s"' % val.replace('"', '\\"')
