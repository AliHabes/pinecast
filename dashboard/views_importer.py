import datetime
import json
import time
import uuid

import itsdangerous
from defusedxml.minidom import parseString as parseXMLString
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest
from django.utils.translation import ugettext
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

import accounts.payment_plans as plans
from . import importer as importer_lib
from . import importer_worker
from .models import AssetImportRequest
from .views import _pmrender
from accounts.decorators import restrict_minimum_plan
from accounts.models import UserSettings
from pinecast.helpers import get_object_or_404, json_response
from podcasts.models import Podcast, PodcastEpisode


signer = itsdangerous.TimestampSigner(settings.SECRET_KEY)


@login_required
def importer(req):
    uset = UserSettings.get_from_user(req.user)
    if uset.plan == plans.PLAN_DEMO:
        return _pmrender(req, 'dashboard/page_importer_upgrade.html', {'reached_limit': False})
    elif plans.has_reached_podcast_limit(uset):
        return _pmrender(req, 'dashboard/page_importer_upgrade.html', {'reached_limit': True})
    else:
        return _pmrender(req, 'dashboard/page_importer.html')


@require_POST
@login_required
@json_response
@restrict_minimum_plan(plans.FEATURE_MIN_IMPORTER)
@importer_lib.handle_format_exceptions
def importer_lookup(req):
    data = req.POST.get('feed')

    try:
        encoded = data.encode('utf-8')
    except Exception as e:
        return {'error': 'invalid encoding'}

    try:
        parsed = parseXMLString(encoded)
    except Exception as e:
        return {'error': 'invalid xml'}

    return importer_lib.get_details(req, parsed)


@login_required
@json_response
@restrict_minimum_plan(plans.FEATURE_MIN_IMPORTER)
def start_import(req):
    try:
        parsed_items = json.loads(req.POST.get('items'))
    except Exception:
        return {'error': ugettext('Invalid JSON')}


    asset_requests = []

    show_image_url = req.POST.get('cover_image')
    try:
        p = Podcast(
            owner=req.user,
            slug=req.POST.get('slug'),
            name=req.POST.get('name'),
            homepage=req.POST.get('homepage'),
            description=req.POST.get('description'),
            language=req.POST.get('language'),
            copyright=req.POST.get('copyright'),
            subtitle=req.POST.get('subtitle'),
            author_name=req.POST.get('author_name', 'Anonymous'),
            is_explicit=req.POST.get('is_explicit', 'false') == 'true',

            # This is just temporary for the feed, just so it's usable in the interim
            cover_image=show_image_url,
        )
        p.save()
        p.set_category_list(req.POST.get('categories'))

        imp_req = AssetImportRequest.create(
            podcast=p,
            expiration=datetime.datetime.now() + datetime.timedelta(hours=1),
            image_source_url=p.cover_image)
        asset_requests.append(imp_req)
    except Exception as e:
        if p:
            try:
                p.delete()
            except Exception:
                pass
        return {'error': ugettext('There was a problem saving the podcast: %s') % unicode(e)}

    created_items = []
    try:
        for item in parsed_items:
            i = PodcastEpisode(
                podcast=p,
                title=item.get('title', '')[:1023],
                subtitle=item.get('subtitle', '')[:1023],
                publish=datetime.datetime.fromtimestamp(time.mktime(item.get('publish', ''))),
                description=item.get('description', ''),
                duration=int(item.get('duration', '0')),
                audio_url=item.get('audio_url', '')[:512],
                audio_size=int(item.get('audio_size', '0')),
                audio_type=item.get('audio_type', 'audio/mp3')[:64],
                image_url=(item.get('image_url', '') or show_image_url)[:512],
                copyright=item.get('copyright', '')[:1023],
                license=item.get('license', '')[:1023],
                awaiting_import=True)
            i.save()
            created_items.append(i)

            # Audio import request
            imp_req = AssetImportRequest.create(
                episode=i,
                expiration=datetime.datetime.now() + datetime.timedelta(hours=3),
                audio_source_url=i.audio_url)
            asset_requests.append(imp_req)


            if i.image_url == p.cover_image: continue

            # Image import request
            imp_req = AssetImportRequest.create(
                episode=i,
                expiration=datetime.datetime.now() + datetime.timedelta(hours=3),
                image_source_url=i.image_url)
            asset_requests.append(imp_req)

    except Exception as e:
        p.delete()
        for i in created_items:
            try:
                i.delete()
            except Exception:
                pass
        return {'error': ugettext('There was a problem saving the podcast items: %s') % unicode(e)}

    for ir in asset_requests:
        ir.save()

    payloads = (x.get_payload() for x in asset_requests)
    payloads = importer_worker.prep_payloads(payloads)
    importer_worker.push_batch(settings.SNS_IMPORT_BUS, payloads)

    return {'error': False, 'ids': [x.id for x in asset_requests]}


@login_required
@json_response
@restrict_minimum_plan(plans.FEATURE_MIN_IMPORTER)
def import_progress(req, podcast_slug):
    p = get_object_or_404(Podcast, slug=podcast_slug, owner=req.user)
    ids = req.GET.get('ids')
    reqs = AssetImportRequest.objects.filter(id__in=ids.split(','))
    total = reqs.count()
    return {'status': sum(1.0 for r in reqs if r.resolved) / total * 100.0}


@login_required
@json_response
@restrict_minimum_plan(plans.FEATURE_MIN_IMPORTER)
def get_request_token(req):
    return {'token': signer.sign(str(uuid.uuid4()))}


@json_response
def check_request_token(req):
    try:
        signer.unsign(req.GET.get('token'), max_age=60)
        return {'success': True}
    except Exception:
        return {'success': False}


@csrf_exempt
@require_POST
@json_response
def import_result(req):
    p = get_object_or_404(AssetImportRequest,
                          access_token=req.POST.get('token'),
                          id=req.POST.get('id'))

    if req.POST.get('failed'):
        p.failure_message = req.POST.get('error')
        p.save()
        return {'success': True}

    try:
        p.resolve(req.POST.get('url'))
    except Exception as e:
        return HttpResponseBadRequest(str(e))

    return {'success': True}
