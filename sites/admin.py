from __future__ import absolute_import

from django.contrib import admin

from .models import Site, SiteBlogPost, SiteLink

admin.site.register(Site)
admin.site.register(SiteBlogPost)
admin.site.register(SiteLink)
