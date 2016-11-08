def escape(val):
    if isinstance(val, (str, unicode)):
        return "'%s'" % val.replace("'", "\\'")
    elif isinstance(val, (int, float, long)):
        return str(val)

    raise Exception('Unknown type %s' % type(val))

def ident(val):
    return '"%s"' % val.replace('"', '\\"')
