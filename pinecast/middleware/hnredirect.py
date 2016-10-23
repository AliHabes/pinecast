from django.conf import settings
from django.http import HttpResponse, HttpResponsePermanentRedirect

PREFERRED_HOSTNAME = 'pinecast.com'

class HostnameRedirect(object):

    def process_request(self, req):
        if settings.DEBUG:
            return None
        hostname = req.META.get('HTTP_HOST')
        if hostname == PREFERRED_HOSTNAME or hostname.endswith('.' + PREFERRED_HOSTNAME):
            return None

        # More Let's Encrypt
        if (hostname == 'pinecast.co' and
            req.path == '/.well-known/acme-challenge/CHjGQzwy6kL5FSQxIt8ObzsUOu2LQpAIWUWeF6zenyw'):
            return HttpResponse('CHjGQzwy6kL5FSQxIt8ObzsUOu2LQpAIWUWeF6zenyw.djl0LF2Nvo-i_b9QJg_lNk4QjgSlIxCaUuPo3U3R-p0')

        elif (hostname == 'pinecast.com.herokudns.com' and
            req.path == '/.well-known/acme-challenge/XNKH55GTiDUDP_h2A7B93bGpIHm5bkKsjRTwWWP4QnA'):
            return HttpResponse('XNKH55GTiDUDP_h2A7B93bGpIHm5bkKsjRTwWWP4QnA.djl0LF2Nvo-i_b9QJg_lNk4QjgSlIxCaUuPo3U3R-p0')

        return HttpResponsePermanentRedirect(
            'https://%s%s' % (PREFERRED_HOSTNAME, req.get_full_path()))
