# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('podcasts', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='PodcastCategory',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('category', models.CharField(max_length=128, choices=[(b'Sports & Recreation/Amateur', b'Sports & Recreation/Amateur'), (b'Music/Electronic/Trip Hop', b'Music/Electronic/Trip Hop'), (b'Music/Folk', b'Music/Folk'), (b'Comedy', b'Comedy'), (b'Health/Kids & Family', b'Health/Kids & Family'), (b'Business/Business News', b'Business/Business News'), (b'Business', b'Business'), (b'Health/Sexuality', b'Health/Sexuality'), (b'Music/Electronic/Jungle', b'Music/Electronic/Jungle'), (b'Games & Hobbies/Automotive', b'Games & Hobbies/Automotive'), (b'News & Politics/Liberal (Left)', b'News & Politics/Liberal (Left)'), (b'Arts/Food', b'Arts/Food'), (b'Music/Electronic/Downtempo', b'Music/Electronic/Downtempo'), (b'Government & Organizations/Regional', b'Government & Organizations/Regional'), (b'Religion & Spirituality/Buddhism', b'Religion & Spirituality/Buddhism'), (b'Music/Electronic/Tribal', b'Music/Electronic/Tribal'), (b'Sports & Recreation/College & High School', b'Sports & Recreation/College & High School'), (b'Religion & Spirituality/Other', b'Religion & Spirituality/Other'), (b'Music/Electronic/Progressive', b'Music/Electronic/Progressive'), (b'Games & Hobbies/Aviation', b'Games & Hobbies/Aviation'), (b'Health/Alternative Health', b'Health/Alternative Health'), (b'Business/Careers', b'Business/Careers'), (b'Education/Language Courses', b'Education/Language Courses'), (b'Government & Organizations/Local', b'Government & Organizations/Local'), (b'Music/Electronic/Disco', b'Music/Electronic/Disco'), (b'Religion & Spirituality/Judaism', b'Religion & Spirituality/Judaism'), (b'Business/Management & Marketing', b'Business/Management & Marketing'), (b'Music/Electronic/Breakbeat', b'Music/Electronic/Breakbeat'), (b'Music', b'Music'), (b'Education', b'Education'), (b'Arts', b'Arts'), (b'Music/Electronic/Ambient', b'Music/Electronic/Ambient'), (b'Games & Hobbies', b'Games & Hobbies'), (b'Science & Medicine', b'Science & Medicine'), (b'Health/Fitness & Nutrition', b'Health/Fitness & Nutrition'), (b'Science & Medicine/Medicine', b'Science & Medicine/Medicine'), (b'Music/Soundtracks', b'Music/Soundtracks'), (b'Arts/Literature', b'Arts/Literature'), (b'Arts/Design', b'Arts/Design'), (b'Music/Electronic/Big Beat', b'Music/Electronic/Big Beat'), (b'Music/Electronic/Garage', b'Music/Electronic/Garage'), (b'Music/Electronic/IDM', b'Music/Electronic/IDM'), (b'Music/Inspirational', b'Music/Inspirational'), (b'Games & Hobbies/Video Games', b'Games & Hobbies/Video Games'), (b'Games & Hobbies/Other Games', b'Games & Hobbies/Other Games'), (b'Arts/Performing Arts', b'Arts/Performing Arts'), (b'Education/K-12', b'Education/K-12'), (b'Technology/Gadgets', b'Technology/Gadgets'), (b'Science & Medicine/Natural Sciences', b'Science & Medicine/Natural Sciences'), (b'Music/Electronic/Techno', b'Music/Electronic/Techno'), (b'Religion & Spirituality/Christianity', b'Religion & Spirituality/Christianity'), (b'Music/Pop', b'Music/Pop'), (b'Music/Electronic', b'Music/Electronic'), (b'Government & Organizations/Non-Profit', b'Government & Organizations/Non-Profit'), (b'Society & Culture/Personal Journals', b'Society & Culture/Personal Journals'), (b'Music/Rock', b'Music/Rock'), (b'Arts/Spoken Word', b'Arts/Spoken Word'), (b'Music/Latin', b'Music/Latin'), (b'Education/Higher Education', b'Education/Higher Education'), (b'Music/Metal', b'Music/Metal'), (b'Technology', b'Technology'), (b'Sports & Recreation/Professional', b'Sports & Recreation/Professional'), (b'Education/Educational Technology', b'Education/Educational Technology'), (b'Sports & Recreation/Outdoor', b'Sports & Recreation/Outdoor'), (b'Music/R&B & Urban', b'Music/R&B & Urban'), (b'Sports & Recreation', b'Sports & Recreation'), (b'Government & Organizations/National', b'Government & Organizations/National'), (b'Health', b'Health'), (b'Religion & Spirituality', b'Religion & Spirituality'), (b'Education/Training', b'Education/Training'), (b'Music/Blues', b'Music/Blues'), (b'Society & Culture/Gay & Lesbian', b'Society & Culture/Gay & Lesbian'), (b'News & Politics/Conservative (Right)', b'News & Politics/Conservative (Right)'), (b'Society & Culture/Places & Travel', b'Society & Culture/Places & Travel'), (b'Music/Easy Listening', b'Music/Easy Listening'), (b'Government & Organizations', b'Government & Organizations'), (b'Technology/IT News', b'Technology/IT News'), (b'Society & Culture/Philosophy', b'Society & Culture/Philosophy'), (b"Music/Electronic/Drum 'n' Bass", b"Music/Electronic/Drum 'n' Bass"), (b'News & Politics', b'News & Politics'), (b'Technology/Software How-To', b'Technology/Software How-To'), (b'Music/Jazz', b'Music/Jazz'), (b'Games & Hobbies/Hobbies', b'Games & Hobbies/Hobbies'), (b'Religion & Spirituality/Hinduism', b'Religion & Spirituality/Hinduism'), (b'Science & Medicine/Social Sciences', b'Science & Medicine/Social Sciences'), (b'Music/Country', b'Music/Country'), (b'Music/Electronic/Hard House', b'Music/Electronic/Hard House'), (b'Society & Culture', b'Society & Culture'), (b'Music/World', b'Music/World'), (b'Music/Reggae', b'Music/Reggae'), (b'Health/Self-Help', b'Health/Self-Help'), (b'Music/Seasonal & Holiday', b'Music/Seasonal & Holiday'), (b'Business/Shopping', b'Business/Shopping'), (b'TV & Film', b'TV & Film'), (b'Arts/Visual Arts', b'Arts/Visual Arts'), (b'Business/Investing', b'Business/Investing'), (b'Society & Culture/History', b'Society & Culture/History'), (b'Arts/Fashion & Beauty', b'Arts/Fashion & Beauty'), (b'Music/Oldies', b'Music/Oldies'), (b'Technology/Podcasting', b'Technology/Podcasting'), (b'Music/Freeform', b'Music/Freeform'), (b'Music/Electronic/Acid House', b'Music/Electronic/Acid House'), (b'Music/Electronic/Trance', b'Music/Electronic/Trance'), (b'Religion & Spirituality/Spirituality', b'Religion & Spirituality/Spirituality'), (b'Music/Alternative', b'Music/Alternative'), (b'Religion & Spirituality/Islam', b'Religion & Spirituality/Islam'), (b'Music/Electronic/House', b'Music/Electronic/House'), (b'Music/Hip-Hop & Rap', b'Music/Hip-Hop & Rap'), (b'Music/New Age', b'Music/New Age')])),
            ],
        ),
        migrations.AddField(
            model_name='podcast',
            name='rss_redirect',
            field=models.URLField(null=True),
        ),
        migrations.AddField(
            model_name='podcast',
            name='stats_base_listens',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='podcast',
            name='subtitle',
            field=models.CharField(default=b'', max_length=512, blank=True),
        ),
        migrations.AlterField(
            model_name='podcastepisode',
            name='description',
            field=models.TextField(default=b''),
        ),
        migrations.AddField(
            model_name='podcastcategory',
            name='podcast',
            field=models.ForeignKey(to='podcasts.Podcast'),
        ),
    ]
