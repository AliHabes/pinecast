from __future__ import absolute_import

from email.Utils import parsedate
from types import StringTypes

from django.utils.translation import ugettext


def handle_format_exceptions(func):
    def wrap(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except FormatException as e:
            return {'error': 'invalid format', 'details': str(e)}
    return wrap


class FormatException(Exception):
    pass


def get_details(req, parsed):
    rss = get_first_tag(parsed, 'rss')

    category_els = rss.getElementsByTagName('itunes:category')
    categories = []
    for cat_el in category_els:
        cat = cat_el.getAttribute('text')
        if not cat: continue
        if cat_el.parentNode.nodeName.lower() == 'itunes:category':
            if not cat_el.parentNode.getAttribute('text'): continue
            cat = '%s/%s' % (cat_el.parentNode.getAttribute('text'), cat)
        categories.append(cat)

    items = []
    data = {
        # Required RSS elements
        'name': first_tag_text(rss, 'title'),
        'homepage': first_tag_text(rss, 'link'),
        'description': first_tag_text(rss, 'description'),

        # Optional RSS elements
        'language': first_tag_text(rss, 'language', 'en-US'),
        'copyright': first_tag_text(rss, 'copyright', ''),
        'author_name': first_tag_text(rss, 'itunes:author', ''),
        'subtitle': first_tag_text(rss, 'itunes:subtitle', ''),
        'is_explicit': first_tag_bool(rss, 'itunes:explicit'),
        'cover_image': first_tag_attr(rss, 'itunes:image', 'href'),
        'categories': categories,
        'copyright': first_tag_text(rss, 'dc:copyright', ''),

        'items': items,
        '__ignored_items': 0,
    }

    item_nodes = rss.getElementsByTagName('item')
    if not item_nodes:
        raise FormatException(ugettext('No <item> nodes in the feed were found'))
    for node in item_nodes:
        audio_url = first_tag_attr(node, 'enclosure', 'url')
        if not audio_url:
            data['__ignored_items'] += 1
            continue

        duration = first_tag_text(node, 'itunes:duration', '0:00')
        dur_tup = list(map(int, duration.split(':')))
        if len(dur_tup) == 1:
            dur_seconds = dur_tup[0]
        elif len(dur_tup) == 2:
            dur_seconds = dur_tup[0] * 60 + dur_tup[1]
        else:
            dur_seconds = dur_tup[-3] * 3600 + dur_tup[-2] * 60 + dur_tup[-1]
        items.append({
            'title': first_tag_text(node, 'title'),
            'description': first_tag_text(node, 'description'),
            'subtitle': first_tag_text(node, 'itunes:subtitle', ''),
            'publish': parsedate(first_tag_text(node, 'pubDate')),
            'image_url': first_tag_attr(node, 'itunes:image', 'href', ''),
            'duration': dur_seconds,
            'audio_url': audio_url,
            'audio_size': first_tag_attr(node, 'enclosure', 'length'),
            'audio_type': first_tag_attr(node, 'enclosure', 'type'),
            'copyright': first_tag_text(node, 'dc:copyright', ''),
            'license': first_tag_text(node, 'dc:rights', ''),
        })

    return data


def parse_date_format(date):
    try:
        return parsedate(date)
    except Exception:
        raise FormatException(ugettext('Could not parse the date "%s"') % date)


def first_tag_text(dom, tag, default=None):
    node = get_first_tag(dom, tag, default)
    if isinstance(node, StringTypes):
        return node

    text = []
    for node in node.childNodes:
        if node.nodeType == node.TEXT_NODE:
            text.append(node.data)
        elif node.nodeType == node.CDATA_SECTION_NODE:
            text.append(node.wholeText)
    return ''.join(text)

def first_tag_attr(dom, tag, attribute, default=''):
    node = get_first_tag(dom, tag, default)
    if isinstance(node, StringTypes): return default
    val = node.getAttribute(attribute)
    if not val:
        if default: return default
        raise FormatException(ugettext('Node <%s> does not have expected attribute %s=""') % (tag, attribute))
    return val

def first_tag_bool(dom, tag, default=False):
    return first_tag_text(dom, tag, 'yes' if default else 'no') == 'yes'

def get_first_tag(dom, tag, default=None):
    elem = dom.getElementsByTagName(tag)
    if not elem and default is None:
        raise FormatException(ugettext('Could not find expected tag <%s> in %s') % (tag, dom.nodeName))
    elif not elem:
        return default

    return elem[0]
