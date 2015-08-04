import pytz
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import ugettext
from django.views.decorators.http import require_POST

from .models import BetaRequest, UserSettings
from dashboard.views import _pmrender
from podmaster.email import request_must_be_confirmed, send_confirmation_email
from podmaster.helpers import reverse, tz_offset


def home(req):
    if not req.user.is_anonymous():
        return redirect('dashboard')

    return redirect('beta_signup')


def login_page(req):
    if not req.user.is_anonymous():
        return redirect('dashboard')

    if not req.POST:
        return render(req, 'login.html')

    try:
        user = User.objects.get(email=req.POST.get('email'))
        password = req.POST.get('password')
    except User.DoesNotExist:
        pass

    if (user and
        user.is_active and
        user.check_password(password)):
        login(req, authenticate(username=user.username, password=password))
        return redirect('dashboard')
    return render(req, 'login.html', {'error': ugettext('Invalid credentials')})


def private_beta_signup(req):
    if not req.user.is_anonymous():
        return redirect('dashboard')

    if not req.POST:
        return render(req, 'pb_signup.html', {'types': BetaRequest.PODCASTER_TYPE})

    email = req.POST.get('email')
    if BetaRequest.objects.filter(email=email).count():
        return render(req, 'pb_signup_done.html')

    request = BetaRequest(
        email=email,
        podcaster_type=req.POST.get('type')
    )
    request.save()
    
    return render(req, 'pb_signup_done.html')


@login_required
def user_settings_page(req):
    return _pmrender(req, 'account/settings.html',
                     {'success': req.GET.get('success'), 'error': req.GET.get('error')})

@login_required
@require_POST
def user_settings_page_savetz(req):
    us = UserSettings.get_from_user(req.user)
    us.tz_offset = tz_offset(req.POST.get('timezone'))
    us.save()
    return redirect(reverse('user_settings') + '?success=tz')

@login_required
@require_POST
def user_settings_page_changeemail(req):
    if User.objects.filter(email=req.POST.get('new_email')).count():
        return redirect(reverse('user_settings') + '?error=eae')
    send_confirmation_email(
        req.user,
        ugettext('[Pinecast] Email change confirmation'),
        ugettext('''
Someone requested a change to your email address on Pinecast. This email is
to verify that you own the email address provided.
'''),
        reverse('user_settings_change_email_finalize') + '?user=%s&email=%s' % (
            req.user.id, req.POST.get('new_email')),
        req.POST.get('new_email')
    )
    return redirect(reverse('user_settings') + '?success=em')

@login_required
@request_must_be_confirmed
def user_settings_page_changeemail_finalize(req):
    user = get_object_or_404(User, id=req.GET.get('user'))
    user.email = req.GET.get('email')
    user.save()
    return redirect(reverse('user_settings') + '?success=emf')
