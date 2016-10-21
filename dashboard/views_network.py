from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import Http404
from django.shortcuts import redirect
from django.utils.translation import ugettext, ugettext_lazy
from django.views.decorators.http import require_POST

import accounts.payment_plans as plans
import analytics.query as analytics_query
import pinecast.email
from accounts.decorators import restrict_minimum_plan
from accounts.models import Network, UserSettings
from pinecast.helpers import get_object_or_404, reverse
from podcasts.models import Podcast, PodcastEpisode
from views import _pmrender, signer


@login_required
@restrict_minimum_plan(plans.PLAN_PRO)
def new_network(req):
    uset = UserSettings.get_from_user(req.user)

    if not req.POST:
        return _pmrender(req, 'dashboard/network/page_new.html')

    try:
        img_url = req.POST.get('image-url')
        net = Network(
            name=req.POST.get('name'),
            owner=req.user,
            image_url=signer.unsign(img_url) if img_url else None
        )
        net.save()
        net.members.add(req.user)
        net.save()
    except Exception as e:
        return _pmrender(req,
                         'dashboard/network/page_new.html',
                         {'error': ugettext('Error while saving network details'),
                          'default': req.POST})

    return redirect('network_dashboard', network_id=net.id)


@login_required
def network_dashboard(req, network_id):
    net = get_object_or_404(Network, deactivated=False, id=network_id, members__in=[req.user])

    net_podcasts = net.podcast_set.all()

    with analytics_query.AsyncContext() as async_ctx:
        top_episodes_query = analytics_query.get_top_episodes(
            [str(p.id) for p in net_podcasts], async_ctx)

    top_episodes = []
    for x in top_episodes_query():
        try:
            episode = PodcastEpisode.objects.get(id=x['episode'])
        except Exception as e:
            continue
        top_episodes.append({'episode': episode, 'count': x['podcast']})

    return _pmrender(req,
                     'dashboard/network/page_dash.html',
                     {'error': req.GET.get('error'),
                      'network': net,
                      'net_podcasts': net_podcasts,
                      'top_episodes': top_episodes})

@require_POST
@login_required
def network_add_show(req, network_id):
    net = get_object_or_404(Network, deactivated=False, id=network_id, members__in=[req.user])
    slug = req.POST.get('slug')
    try:
        pod = Podcast.objects.get(slug=slug)
    except Podcast.DoesNotExist:
        return redirect(reverse('network_dashboard', network_id=net.id) + '?error=aslg#shows,add-show')
    else:
        if pod.owner != req.user:
            return redirect(reverse('network_dashboard', network_id=net.id) + '?error=nown#shows,add-show')
        pod.networks.add(net)
        pod.save()
    return redirect('network_dashboard', network_id=net.id)


@require_POST
@login_required
def network_add_member(req, network_id):
    net = get_object_or_404(Network, deactivated=False, id=network_id, members__in=[req.user])

    try:
        user = User.objects.get(email=req.POST.get('email'))
    except User.DoesNotExist:
        return redirect(reverse('network_dashboard', network_id=network_id) + '?error=udne#members,add-member')

    net.members.add(user)
    net.save()
    pinecast.email.send_notification_email(
        user,
        ugettext('[Pinecast] You have been added to "%s"') % net.name,
        ugettext('''
We are emailing you to let you know that you were added to the network
"%s". No action is required on your part. If you log in to Pinecast,
you will now have read and write access to all of the podcasts in the
network, and will be able to add your own podcasts to the network.
        ''') % net.name
    )

    return redirect(reverse('network_dashboard', network_id=net.id) + '#members')


@require_POST
@login_required
def network_edit(req, network_id):
    net = get_object_or_404(Network, deactivated=False, id=network_id, members__in=[req.user])

    try:
        net.name = req.POST.get('name')
        net.image_url = signer.unsign(req.POST.get('image-url')) if req.POST.get('image-url') else None
        net.save()
    except Exception as e:
        # TODO: maybe handle this better?
        pass

    return redirect('network_dashboard', network_id=net.id)


@require_POST
@login_required
def network_deactivate(req, network_id):
    net = get_object_or_404(Network, deactivated=False, id=network_id, owner=req.user)

    if req.POST.get('confirm') != 'doit':
        return redirect('dashboard')

    net.deactivated = True
    net.save()

    return redirect('dashboard')


@require_POST
@login_required
def network_remove_podcast(req, network_id, podcast_slug):
    net = get_object_or_404(Network, deactivated=False, id=network_id, members__in=[req.user])
    pod = get_object_or_404(Podcast, slug=podcast_slug, networks__in=[net])

    # We don't need to confirm if the user is the owner.
    if pod.owner == req.user:
        pod.networks.remove(net)
        pod.save()
        return redirect('network_dashboard', network_id=net.id)

    if req.user != net.owner:
        raise Http404()


    pod.networks.remove(net)
    pod.save()

    return redirect('network_dashboard', network_id=net.id)


@require_POST
@login_required
def network_remove_member(req, network_id, member_id):
    net = get_object_or_404(Network, deactivated=False, id=network_id, members__in=[req.user])
    user = get_object_or_404(User, id=member_id)

    if not net.members.filter(username=user.username).count():
        raise Http404()

    # We don't need to confirm if the user is the owner.
    if net.owner == user:
        return redirect('network_dashboard', network_id=net.id)

    pods = Podcast.objects.filter(owner=user, networks__in=[net])

    for pod in pods:
        pod.networks.remove(net)
        pod.save()
    net.members.remove(user)
    net.save()

    return redirect(reverse('network_dashboard', network_id=net.id) + '#members')
