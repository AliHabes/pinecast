from __future__ import absolute_import

from django.contrib import admin

from .models import AssetImportRequest, Collaborator


class AssetImportRequestAdmin(admin.ModelAdmin):
    model = AssetImportRequest
    list_display = ('__str__', 'asset_type', 'trace_podcast', 'episode', 'status')


admin.site.register(AssetImportRequest, AssetImportRequestAdmin)
admin.site.register(Collaborator)
