from __future__ import absolute_import

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
from pinecast.helpers import get_object_or_404, populate_context, render, reverse, round_now
from pinecast.signatures import signer_nots as signer
from podcasts.models import Podcast, PodcastEpisode


def get_network(req, id):
    if req.user.is_staff:
        return get_object_or_404(Network, deactivated=False, id=id)
    else:
        return get_object_or_404(Network, deactivated=False, id=id, members__in=[req.user])


@login_required
@restrict_minimum_plan(plans.PLAN_PRO)
def new_network(req):
    uset = UserSettings.get_from_user(req.user)

    if not req.POST:
        return render(req, 'dashboard/network/page_new.html')

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
        return render(req,
                         'dashboard/network/page_new.html',
                         {'error': ugettext('Error while saving network details'),
                          'default': req.POST})

    return redirect('network_dashboard', network_id=net.id)


@login_required
def network_dashboard(req, network_id):
    net = get_network(req, network_id)

    net_podcasts = net.podcast_set.all()
    pod_map = {str(p.id): p for p in net_podcasts}

    top_episodes_data = analytics_query.get_top_episodes([str(p.id) for p in net_podcasts])

    top_episodes = []
    top_episodes_listing = sorted(top_episodes_data.items(), key=lambda x: -1 * x[1])[:75]
    fetched_eps_map = {
        str(ep.id): ep for
        ep in
        PodcastEpisode.objects.filter(id__in=[x for x, _ in top_episodes_listing])
    }
    for ep_id, count in top_episodes_listing:
        episode = fetched_eps_map.get(ep_id)
        if not episode:
            continue
        top_episodes.append({
            'count': count,
            'episode': episode,
            'podcast': pod_map[str(episode.podcast_id)],
        })

    upcoming_episodes = PodcastEpisode.objects.filter(
        podcast__in=net_podcasts,
        publish__gt=round_now())

    ctx = {
        'error': req.GET.get('error'),
        'network': net,
        'net_podcasts': net_podcasts,
        'net_podcasts_map': pod_map,
        'top_episodes': top_episodes,
        'upcoming_episodes': list(upcoming_episodes),
    }
    populate_context(req.user, ctx)
    net_pod_ids = [x.id for x in net_podcasts]
    ctx['net_pod_ids'] = net_pod_ids
    ctx['has_pods_to_add'] = any(pod.id not in net_pod_ids for pod in ctx['podcasts'])

    return render(req, 'dashboard/network/page_dash.html', ctx)

@require_POST
@login_required
def network_add_show(req, network_id):
    net = get_network(req, network_id)
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
    return redirect(reverse('network_dashboard', network_id=net.id) + '#shows')


@require_POST
@login_required
def network_add_member(req, network_id):
    net = get_network(req, network_id)

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
    net = get_network(req, network_id)

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
    net = get_network(req, network_id)
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
    net = get_network(req, network_id)
    user = get_object_or_404(User, id=member_id)

    if not net.members.filter(username=user.username).exists():
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
