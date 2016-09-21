import datetime

from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import redirect
from django.views.decorators.http import require_POST

from accounts import payment_plans
from accounts.models import Network, UserSettings
from pinecast.helpers import get_object_or_404, json_response, reverse
from podcasts.models import Podcast
from sites.models import Site, SiteBlogPost, SiteLink
from views import _pmrender, get_podcast, signer


def get_site(req, podcast_slug):
    pod = get_object_or_404(Podcast, slug=podcast_slug)
    if (pod.owner != req.user and
        not Network.objects.filter(
            deactivated=False, members__in=[req.user], podcast__in=[pod]).count()):
        raise Http404()
    return pod.site

@login_required
def new_site(req, podcast_slug):
    pod = get_podcast(req, podcast_slug)

    if not payment_plans.minimum(
        UserSettings.get_from_user(pod.owner).plan,
        payment_plans.FEATURE_MIN_SITES):
        raise Http404()

    data = {
        'podcast': pod,
        'themes': Site.SITE_THEMES,
    }

    if not req.POST:
        return _pmrender(req, 'dashboard/sites/page_new.html', data)

    try:
        site = Site(
            podcast=pod,
            theme=req.POST.get('theme'),
            cover_image_url=signer.unsign(req.POST.get('cover-url')) if req.POST.get('cover-url') else None,
            logo_url=signer.unsign(req.POST.get('logo-url')) if req.POST.get('logo-url') else None,
            analytics_id=req.POST.get('analytics_id'),
            itunes_url=req.POST.get('itunes_url'),
            stitcher_url=req.POST.get('stitcher_url')
        )
        site.save()
    except Exception as e:
        data.update(error=True, default=req.POST)
        return _pmrender(req, 'dashboard/sites/page_new.html', data)
    else:
        return redirect('site_options', podcast_slug=podcast_slug)


@login_required
def site_options(req, podcast_slug):
    site = get_site(req, podcast_slug)
    return _pmrender(req, 'dashboard/sites/page_site.html', {'site': site, 'error': req.GET.get('error')})

@login_required
def edit_site(req, podcast_slug):
    site = get_site(req, podcast_slug)

    data = {
        'site': site,
        'themes': Site.SITE_THEMES,
    }

    if not req.POST:
        return _pmrender(req, 'dashboard/sites/page_edit.html', data)

    try:
        site.theme = req.POST.get('theme')
        site.cover_image_url = signer.unsign(req.POST.get('cover-url')) if req.POST.get('cover-url') else None
        site.logo_url = signer.unsign(req.POST.get('logo-url')) if req.POST.get('logo-url') else None
        site.analytics_id = req.POST.get('analytics_id')
        site.itunes_url = req.POST.get('itunes_url')
        site.stitcher_url = req.POST.get('stitcher_url')
        site.save()
    except Exception as e:
        data.update(error=True, default=req.POST)
        return _pmrender(req, 'dashboard/sites/page_edit.html', data)
    else:
        return redirect('site_options', podcast_slug=podcast_slug)

@login_required
def delete_site(req, podcast_slug):
    site = get_site(req, podcast_slug)

    data = {'site': site}

    if not req.POST:
        return _pmrender(req, 'dashboard/sites/page_delete.html', data)
    elif req.POST.get('slug') != podcast_slug:
        return redirect('site_options', podcast_slug=podcast_slug)

    site.delete()
    return redirect(
        reverse('podcast_dashboard', podcast_slug=podcast_slug) + '#tab-site'
    )


@login_required
@require_POST
def add_link(req, podcast_slug):
    site = get_site(req, podcast_slug)

    try:
        url = req.POST.get('url')
        if not url.startswith('http://') and not url.startswith('https://'):
            raise Exception('Invalid scheme')

        SiteLink(site=site, title=req.POST.get('title'), url=url).save()
        return redirect('site_options', podcast_slug=podcast_slug)
    except Exception as e:
        return redirect(reverse('site_options', podcast_slug=podcast_slug) + '?error=link')

@login_required
@require_POST
def remove_link(req, podcast_slug):
    site = get_site(req, podcast_slug)
    try:
        link = SiteLink.objects.get(id=req.POST.get('id'))
        link.delete()
    except Exception:
        pass
    return redirect('site_options', podcast_slug=podcast_slug)


@login_required
def add_blog_post(req, podcast_slug):
    site = get_site(req, podcast_slug)

    if not payment_plans.minimum(
        UserSettings.get_from_user(site.podcast.owner).plan,
        payment_plans.FEATURE_MIN_BLOG):
        raise Http404()

    data = {'site': site}

    if not req.POST:
        return _pmrender(req, 'dashboard/sites/blog/page_new.html', data)

    try:
        naive_publish = datetime.datetime.strptime(req.POST.get('publish'), '%Y-%m-%dT%H:%M') # 2015-07-09T12:00
        adjusted_publish = naive_publish - UserSettings.get_from_user(req.user).get_tz_delta()
        post = SiteBlogPost(
            site=site,
            title=req.POST.get('title'),
            slug=req.POST.get('slug'),
            body=req.POST.get('body'),
            publish=adjusted_publish
        )
        post.save()
    except Exception as e:
        data.update(error=True, default=req.POST)
        return _pmrender(req, 'dashboard/sites/blog/page_new.html', data)
    else:
        return redirect('site_manage_blog', podcast_slug=podcast_slug)

@login_required
def manage_blog(req, podcast_slug):
    site = get_site(req, podcast_slug)

    if not payment_plans.minimum(
        UserSettings.get_from_user(site.podcast.owner).plan,
        payment_plans.FEATURE_MIN_BLOG):
        raise Http404()

    return _pmrender(req, 'dashboard/sites/blog/page_manage.html',
                     {'site': site, 'posts': site.siteblogpost_set.all().order_by('-publish')})

@login_required
def edit_blog_post(req, podcast_slug, post_slug):
    site = get_site(req, podcast_slug)
    post = get_object_or_404(SiteBlogPost, site=site, slug=post_slug)

    if not req.POST:
        return _pmrender(req, 'dashboard/sites/blog/page_edit.html', {'site': site, 'post': post})
    try:
        naive_publish = datetime.datetime.strptime(req.POST.get('publish'), '%Y-%m-%dT%H:%M') # 2015-07-09T12:00
        adjusted_publish = naive_publish - UserSettings.get_from_user(req.user).get_tz_delta()
        post.title = req.POST.get('title')
        post.slug = req.POST.get('slug')
        post.body = req.POST.get('body')
        post.publish = adjusted_publish
        post.save()
    except Exception as e:
        data.update(error=True, default=req.POST)
        return _pmrender(req, 'dashboard/sites/blog/page_edit.html', data)
    else:
        return redirect('site_manage_blog', podcast_slug=podcast_slug)


@login_required
def remove_blog_post(req, podcast_slug):
    site = get_site(req, podcast_slug)
    post = get_object_or_404(SiteBlogPost, site=site, slug=req.POST.get('slug'))

    post.delete()
    return redirect('site_manage_blog', podcast_slug=podcast_slug)
