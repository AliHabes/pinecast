from urllib import quote

from django.shortcuts import redirect
from django.utils.translation import ugettext

from payments.models import TipUser
from dashboard.views import _pmrender
from pinecast.email import send_anon_confirmation_email as send_email, validate_confirmation
from pinecast.helpers import reverse


def no_session(req, ctx):
    if not req.POST:
        return _pmrender(req, 'payments/tip_jar/login.html', ctx)

    has_user = False
    if req.POST.get('email'):
        email = req.POST.get('email')
        tip_user = None
        try:
            tip_user = TipUser.objects.get(email_address=email)
            has_user = True
        except TipUser.DoesNotExist:
            try:
                tip_user = TipUser(email_address=email)
                tip_user.save()
                has_user = True
            except Exception as e:
                pass

        if has_user:
            send_email(
                email,
                ugettext('Leave a tip for %s') % ctx['podcast'].name,
                ugettext(
                    'Thanks for verifying your email! Click the link below '
                    'to choose your level of support for %s.' %
                        ctx['podcast'].name),
                reverse('tip_jar', podcast_slug=ctx['podcast'].slug) +
                    '?email=%s' % quote(email))

    if has_user:
        return _pmrender(req, 'payments/tip_jar/check_email.html', ctx)

    ctx['error'] = ugettext('That email address did not work.')
    return _pmrender(req, 'payments/tip_jar/login.html', ctx)


def create_session(req, ctx):
    validates = validate_confirmation(req)
    email = req.GET.get('email')
    if not validates or not email:
        return redirect(
            reverse('tip_jar', podcast_slug=ctx['podcast'].slug) +
            '?error=bad_token')

    # This should never throw, unless the TipUser was manually deleted.
    # The validated URL should never have been created if a TipUser was not
    # saved for that email.
    tip_user = TipUser.objects.get(email_address=email)

    req.session['pay_session'] = tip_user.id
    return tip_flow(req, ctx, tip_user)


def tip_flow(req, ctx, tip_user=None):
    # Same logic here as above.
    tip_user = tip_user or TipUser.objects.get(id=req.session['pay_session'])

    ctx['tipper'] = tip_user
    return _pmrender(req, 'payments/tip_jar/main.html', ctx)
