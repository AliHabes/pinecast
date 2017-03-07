from __future__ import absolute_import

import datetime

from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import redirect
from django.views.decorators.http import require_GET, require_POST

from .views import get_podcast
from accounts import payment_plans
from accounts.models import Network, UserSettings
from pinecast.helpers import get_object_or_404, json_response, render, reverse
from pinecast.signatures import signer_nots as signer
from podcasts.models import Podcast
from sites.models import Site, SiteBlogPost, SiteLink, SitePage


def get_site(req, podcast_slug):
    pod = get_object_or_404(Podcast, slug=podcast_slug)
    if (pod.owner != req.user and
        not Network.objects.filter(
            deactivated=False, members__in=[req.user], podcast__in=[pod]).exists()):
        raise Http404()
    return pod.site

@require_POST
@login_required
def new_site(req, podcast_slug):
    pod = get_podcast(req, podcast_slug)

    if not payment_plans.minimum(
        UserSettings.get_from_user(pod.owner).plan,
        payment_plans.FEATURE_MIN_SITES):
        raise Http404()

    try:
        site = Site(
            podcast=pod,
            theme=req.POST.get('theme'),
            cover_image_url=signer.unsign(req.POST.get('cover-url')) if req.POST.get('cover-url') else None,
            logo_url=signer.unsign(req.POST.get('logo-url')) if req.POST.get('logo-url') else None,
            analytics_id=req.POST.get('analytics_id'),
            itunes_url=req.POST.get('itunes_url'),
            stitcher_url=req.POST.get('stitcher_url'),
            show_itunes_banner=req.POST.get('show_itunes_banner') == 'true')
        site.save()
    except Exception as e:
        return redirect(reverse('podcast_dashboard', podcast_slug=podcast_slug) + '?error=true#site')
    else:
        return redirect(reverse('podcast_dashboard', podcast_slug=podcast_slug) + '#site')

@require_POST
@login_required
def edit_site(req, podcast_slug):
    site = get_site(req, podcast_slug)
    try:
        site.theme = req.POST.get('theme')
        site.cover_image_url = signer.unsign(req.POST.get('cover-url')) if req.POST.get('cover-url') else None
        site.logo_url = signer.unsign(req.POST.get('logo-url')) if req.POST.get('logo-url') else None
        site.analytics_id = req.POST.get('analytics_id')
        site.itunes_url = req.POST.get('itunes_url')
        site.stitcher_url = req.POST.get('stitcher_url')
        site.show_itunes_banner = req.POST.get('show_itunes_banner') == 'true'
        site.custom_css = req.POST.get('custom_css')
        site.custom_cname = req.POST.get('custom_cname')

        us = UserSettings.get_from_user(site.podcast.owner)
        if payment_plans.minimum(us.plan, payment_plans.FEATURE_MIN_BLOG):
            site.disqus_url = req.POST.get('disqus_url')
        if payment_plans.minimum(us.plan, payment_plans.FEATURE_MIN_SITE_FAVICON):
            site.favicon_url = signer.unsign(req.POST.get('favicon-url')) if req.POST.get('favicon-url') else None

        site.save()
    except Exception as e:
        return redirect(reverse('podcast_dashboard', podcast_slug=podcast_slug) + '?error=true#settings,site-options')
    else:
        return redirect(reverse('podcast_dashboard', podcast_slug=podcast_slug) + '#settings,site-options')

@require_POST
@login_required
def delete_site(req, podcast_slug):
    try:
        site = get_site(req, podcast_slug)
        site.delete()
    except Exception:
        pass
    return redirect(reverse('podcast_dashboard', podcast_slug=podcast_slug) + '#site')


@require_POST
@login_required
def add_link(req, podcast_slug):
    site = get_site(req, podcast_slug)

    try:
        url = req.POST.get('url')
        if not url.startswith('http://') and not url.startswith('https://'):
            raise Exception('Invalid scheme')

        SiteLink(site=site, title=req.POST.get('title'), url=url).save()
    except Exception as e:
        return redirect(reverse('podcast_dashboard', podcast_slug=podcast_slug) + '?error=slink#site,links')
    else:
        return redirect(reverse('podcast_dashboard', podcast_slug=podcast_slug) + '#site,links')

@require_POST
@login_required
def remove_link(req, podcast_slug):
    site = get_site(req, podcast_slug)
    try:
        link = SiteLink.objects.get(id=req.POST.get('id'), site=site)
        link.delete()
    except Exception:
        pass
    return redirect(reverse('podcast_dashboard', podcast_slug=podcast_slug) + '#settings,site-options')


@require_POST
@login_required
def add_blog_post(req, podcast_slug):
    site = get_site(req, podcast_slug)

    if not payment_plans.minimum(
        UserSettings.get_from_user(site.podcast.owner).plan,
        payment_plans.FEATURE_MIN_BLOG):
        raise Http404()

    try:
        publis_parsed = datetime.datetime.strptime(req.POST.get('publish', '').split('.')[0], '%Y-%m-%dT%H:%M:%S')
        post = SiteBlogPost(
            site=site,
            title=req.POST.get('title'),
            slug=req.POST.get('slug'),
            body=req.POST.get('body'),
            publish=publis_parsed,
            disable_comments=req.POST.get('disable_comments') == 'true')
        post.save()
    except Exception as e:
        print(e)
        return redirect(reverse('podcast_dashboard', podcast_slug=podcast_slug) + '?error=sblog#site,blog')
    else:
        return redirect(reverse('podcast_dashboard', podcast_slug=podcast_slug) + '#site,blog')

@login_required
def edit_blog_post(req, podcast_slug, post_slug):
    site = get_site(req, podcast_slug)
    post = get_object_or_404(SiteBlogPost, site=site, slug=post_slug)

    if not req.POST:
        return render(req, 'dashboard/sites/blog/page_edit.html', {'site': site, 'post': post})
    try:
        naive_publish = datetime.datetime.strptime(req.POST.get('publish', '').split('.')[0], '%Y-%m-%dT%H:%M:%S') # 2015-07-09T12:00
        adjusted_publish = naive_publish - UserSettings.get_from_user(req.user).get_tz_delta()
        post.title = req.POST.get('title')
        post.slug = req.POST.get('slug')
        post.body = req.POST.get('body')
        post.publish = adjusted_publish
        post.disable_comments = req.POST.get('disable_comments') == 'true'
        post.save()
    except Exception as e:
        data.update(error=True, default=req.POST)
        return render(req, 'dashboard/sites/blog/page_edit.html', data)
    else:
        return redirect(reverse('podcast_dashboard', podcast_slug=podcast_slug) + '#site,blog')


@login_required
def remove_blog_post(req, podcast_slug):
    site = get_site(req, podcast_slug)
    post = get_object_or_404(SiteBlogPost, site=site, slug=req.POST.get('slug'))

    post.delete()
    return redirect(reverse('podcast_dashboard', podcast_slug=podcast_slug) + '#site,blog')


@login_required
@require_GET
@json_response
def slug_available(req, podcast_slug):
    site = get_site(req, podcast_slug)
    try:
        SitePage.objects.get(slug=req.GET.get('slug'))
    except SitePage.DoesNotExist:
        return {'valid': True}
    else:
        return {'valid': False}


@login_required
@require_POST
def new_page(req, podcast_slug):
    site = get_site(req, podcast_slug)

    try:
        page = SitePage(
            site=site,
            title=req.POST.get('title'),
            slug=req.POST.get('slug'),
            page_type=req.POST.get('page_type'),
            body=SitePage.get_body_from_req(req),
        )
        page.save()
    except Exception as e:
        pass

    return redirect(reverse('podcast_dashboard', podcast_slug=podcast_slug) + '#site,options')

@login_required
def edit_page(req, podcast_slug, page_slug):
    site = get_site(req, podcast_slug)
    page = get_object_or_404(SitePage, site=site, slug=page_slug)

    if not req.POST:
        return render(req, 'dashboard/sites/pages/page_edit.html', {'site': site, 'page': page})
    try:
        page.title = req.POST.get('title')
        page.body = SitePage.get_body_from_req(req, page.page_type)
        page.save()
    except Exception as e:
        data.update(error=True, default=req.POST)
        return render(req, 'dashboard/sites/pages/page_edit.html', data)
    else:
        return redirect(reverse('podcast_dashboard', podcast_slug=podcast_slug) + '#site')

@login_required
@require_POST
def delete_page(req, podcast_slug, page_slug):
    site = get_site(req, podcast_slug)
    page = get_object_or_404(SitePage, site=site, slug=page_slug)
    page.delete()

    return redirect(reverse('podcast_dashboard', podcast_slug=podcast_slug) + '#site')
