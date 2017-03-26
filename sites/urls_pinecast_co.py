from __future__ import absolute_import

from django.conf import settings
from django.conf.urls import include, url
from django.http import HttpResponse


def twitter_cards(req):
    return HttpResponse('''
    <!DOCTYPE html>
    <html>
        <head>
            <title>Twitter Cards Embed</title>
            <meta name="twitter:card" content="player">
            <meta name="twitter:site" content="@getpinecast">
            <meta name="twitter:title" content="Dummy Embed">
            <meta name="twitter:description" content="Dummy Description">
            <meta name="twitter:image" content="https://pinecast.com/static/img/256x256.png">
            <meta name="twitter:player" content="https://pinecast.com/player/7a2504ab-5e48-4a13-9b8c-f610b9f4b3bc">
            <meta name="twitter:player:width" content="480">
            <meta name="twitter:player:height" content="60">
            <meta name="twitter:player:stream" content="https://pinecast.com/listen/7a2504ab-5e48-4a13-9b8c-f610b9f4b3bc.mp3">
            <meta name="twitter:player:stream:content_type" content="audio/mp3">
        </head>
        <body>
            Nothing to see here.
        </body>
    </html>
    '''.strip())


urlpatterns = [
    url(r'^twitter/cards$', twitter_cards),
]
