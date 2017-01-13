from __future__ import absolute_import

from django.conf.urls import url

from . import views, views_collaborators, views_importer, views_network, views_sites


urlpatterns = [
    url(r'^$', views.dashboard, name='dashboard'),
    url(r'^/new_podcast$', views.new_podcast, name='new_podcast'),
    url(r'^/podcast/(?P<podcast_slug>[\w-]+)$', views.podcast_dashboard, name='podcast_dashboard'),
    url(r'^/podcast/(?P<podcast_slug>[\w-]+)/delete$', views.delete_podcast, name='delete_podcast'),
    url(r'^/podcast/(?P<podcast_slug>[\w-]+)/edit$', views.edit_podcast, name='edit_podcast'),
    url(r'^/podcast/(?P<podcast_slug>[\w-]+)/new_episode', views.podcast_new_ep, name='new_episode'),
    url(r'^/podcast/(?P<podcast_slug>[\w-]+)/episode/(?P<episode_id>[\w-]+)#(?P<tab>[\w-]+)$', views.podcast_episode, name='podcast_episode'),
    url(r'^/podcast/(?P<podcast_slug>[\w-]+)/episode/(?P<episode_id>[\w-]+)$', views.podcast_episode, name='podcast_episode'),
    url(r'^/podcast/(?P<podcast_slug>[\w-]+)/episode/(?P<episode_id>[\w-]+)/delete$', views.delete_podcast_episode, name='delete_podcast_episode'),
    url(r'^/podcast/(?P<podcast_slug>[\w-]+)/episode/(?P<episode_id>[\w-]+)/publish_now$', views.podcast_episode_publish_now, name='podcast_episode_publish_now'),
    url(r'^/podcast/(?P<podcast_slug>[\w-]+)/episode/(?P<episode_id>[\w-]+)/edit$', views.edit_podcast_episode, name='edit_podcast_episode'),
    url(r'^/podcast/(?P<podcast_slug>[\w-]+)/new_collaborator', views_collaborators.new_collaborator, name='new_collaborator'),
    url(r'^/podcast/(?P<podcast_slug>[\w-]+)/delete_collaborator', views_collaborators.delete_collaborator, name='delete_collaborator'),

    url(r'^/network/new$', views_network.new_network, name='new_network'),
    url(r'^/network/(?P<network_id>[\w-]+)$', views_network.network_dashboard, name='network_dashboard'),
    url(r'^/network/(?P<network_id>[\w-]+)/add_show$', views_network.network_add_show, name='network_add_show'),
    url(r'^/network/(?P<network_id>[\w-]+)/add_member$', views_network.network_add_member, name='network_add_member'),
    url(r'^/network/(?P<network_id>[\w-]+)/edit$', views_network.network_edit, name='network_edit'),
    url(r'^/network/(?P<network_id>[\w-]+)/deactivate$', views_network.network_deactivate, name='network_deactivate'),
    url(r'^/network/(?P<network_id>[\w-]+)/remove_podcast/(?P<podcast_slug>[\w-]+)$', views_network.network_remove_podcast, name='network_remove_podcast'),
    url(r'^/network/(?P<network_id>[\w-]+)/remove_member/(?P<member_id>[\w]+)$', views_network.network_remove_member, name='network_remove_member'),

    url(r'^/sites/new/(?P<podcast_slug>[\w-]+)$', views_sites.new_site, name='new_site'),
    url(r'^/sites/options/(?P<podcast_slug>[\w-]+)/edit$', views_sites.edit_site, name='edit_site'),
    url(r'^/sites/options/(?P<podcast_slug>[\w-]+)/add_link$', views_sites.add_link, name='site_add_link'),
    url(r'^/sites/options/(?P<podcast_slug>[\w-]+)/remove_link$', views_sites.remove_link, name='site_remove_link'),
    url(r'^/sites/options/(?P<podcast_slug>[\w-]+)/delete_site$', views_sites.delete_site, name='delete_site'),
    url(r'^/sites/options/(?P<podcast_slug>[\w-]+)/pages/new$', views_sites.new_page, name='site_new_page'),
    url(r'^/sites/options/(?P<podcast_slug>[\w-]+)/pages/slug_available$', views_sites.slug_available, name='site_slug_available'),
    url(r'^/sites/options/(?P<podcast_slug>[\w-]+)/pages/edit/(?P<page_slug>[\w-]+)$', views_sites.edit_page, name='site_edit_page'),
    url(r'^/sites/options/(?P<podcast_slug>[\w-]+)/pages/delete/(?P<page_slug>[\w-]+)$', views_sites.delete_page, name='site_delete_page'),
    url(r'^/sites/options/(?P<podcast_slug>[\w-]+)/blog/add$', views_sites.add_blog_post, name='site_add_blog_post'),
    url(r'^/sites/options/(?P<podcast_slug>[\w-]+)/blog/edit/(?P<post_slug>[\w-]+)$', views_sites.edit_blog_post, name='site_blog_post'),
    url(r'^/sites/options/(?P<podcast_slug>[\w-]+)/blog/remove$', views_sites.remove_blog_post, name='site_remove_blog_post'),

    url(r'^/feedback/remove/(?P<podcast_slug>[\w-]+)/(?P<comment_id>[\w-]+)$', views.delete_comment, name='delete_comment'),

    url(r'^/import/feed$', views_importer.importer_lookup),

    url(r'^/services/slug_available$', views.slug_available, name='slug_available'),
    url(r'^/services/getUploadURL/(?P<podcast_slug>([\w-]+|\$none|\$net|\$site))/(?P<type_>[\w]+)$', views.get_upload_url, name='get_upload_url'),

    url(r'^/services/start_import$', views_importer.start_import),
    url(r'^/services/import_progress/(?P<podcast_slug>[\w-]+)$', views_importer.import_progress),
    url(r'^/services/import_result$', views_importer.import_result),
    url(r'^/services/get_request_token$', views_importer.get_request_token),
    url(r'^/services/check_request_token$', views_importer.check_request_token, name='check_request_token'),

    url(r'^/services/get_episodes$', views.get_episodes),
]
