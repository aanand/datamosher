#!/usr/bin/env python2
# -*- coding: utf-8 -*- #

from __future__ import unicode_literals

from twitterbot import TwitterBot

from extensions.video import Processor
from extensions.datamosh import MOSH_TYPES
from extensions.sql_storage import SQLStorage

import arrow
from bs4 import BeautifulSoup

import random
import os
import logging
import urllib
import re
from io import BytesIO


URL_PATTERN = re.compile(r'^https?://twitter\.com/(\w+)/status/(\d+)/photo/1$')


class DataMosher(TwitterBot):
    def bot_init(self):
        self.config['storage'] = SQLStorage(os.environ['DATABASE_URL'])

        self.config['api_key'] = os.environ['TWITTER_CONSUMER_KEY']
        self.config['api_secret'] = os.environ['TWITTER_CONSUMER_SECRET']
        self.config['access_key'] = os.environ['TWITTER_ACCESS_TOKEN']
        self.config['access_secret'] = os.environ['TWITTER_ACCESS_TOKEN_SECRET']

        # use this to define a (min, max) random range of how often to tweet
        # e.g., self.config['tweet_interval_range'] = (5*60, 10*60) # tweets every 5-10 minutes
        self.config['tweet_interval_range'] = (1*60, 3*60*60)

        # only reply to tweets that specifically mention the bot
        self.config['reply_direct_mention_only'] = False

        # only include bot followers (and original tweeter) in @-replies
        self.config['reply_followers_only'] = False

        # fav any tweets that mention this bot?
        self.config['autofav_mentions'] = False

        # fav any tweets containing these keywords?
        self.config['autofav_keywords'] = []

        # follow back all followers?
        self.config['autofollow'] = True

        # ignore home timeline tweets which mention other accounts?
        self.config['ignore_timeline_mentions'] = False

        # ignore retweets in the home timeline
        self.config['ignore_timeline_retweets'] = True

        # max number of times to reply to someone within the moving window
        self.config['reply_threshold'] = 3

        # length of the moving window, in seconds
        self.config['recent_replies_window'] = 20*60

        # probability of replying to a matching timeline tweet
        self.config['timeline_reply_probability'] = float(os.environ.get('TIMELINE_REPLY_PROBABILITY') or '0.05')

        self.config['silent_mode'] = (int(os.environ.get('SILENT_MODE') or '1') != 0)

    def on_scheduled_tweet(self):
        pass

    def on_mention(self, tweet, prefix):
        if not self.check_reply_threshold(tweet, prefix):
            return

        try:
            self.reply_to_tweet(tweet, prefix)
        except Exception as e:
            self.log(str(e))
            return

    def on_timeline(self, tweet, prefix):
        if not self.check_reply_threshold(tweet, prefix):
            return

        if random.random() > self.config['timeline_reply_probability']:
            self.log("Failed dice roll. Not responding to {}".format(self._tweet_url(tweet)))
            return

        try:
            self.reply_to_tweet(tweet, prefix)
        except Exception as e:
            self.log(str(e))
            return

    def reply_to_tweet(self, tweet, prefix):
        video_url = self.get_gif_video_url(tweet)
        if video_url is None:
            self.log("Couldn't find a gif video URL for {}".format(self._tweet_url(tweet)))
            return

        mosh_type = None
        for mt in MOSH_TYPES:
            if '#{}'.format(mt) in tweet.text.split():
                mosh_type = mt
                break

        if not mosh_type:
            mosh_type = random.choice(MOSH_TYPES)

        text = '{} #{}'.format(prefix, mosh_type)
        filename = self.generate_gif(video_url, mosh_type=mosh_type)

        if self._is_silent():
            self.log("Silent mode is on. Would've responded to {} with '{} {}'".format(
                self._tweet_url(tweet), text, filename))
            return

        self.post_tweet(
            text,
            reply_to=tweet,
            media=filename,
        )
        self.update_reply_threshold(tweet, prefix)

    def _is_silent(self):
        return self.config['silent_mode']

    def check_reply_threshold(self, tweet, prefix):
        self.trim_recent_replies()
        screen_names = self.get_screen_names(prefix)
        over_threshold = [sn for sn in screen_names if self.over_reply_threshold(sn)]

        if len(over_threshold) > 0:
            self.log("Over reply threshold for {}. Not responding to {}".format(", ".join(over_threshold), self._tweet_url(tweet)))
            return False

        return True

    def over_reply_threshold(self, screen_name):
        replies = [r for r in self.recent_replies() if screen_name in r['screen_names']]
        return len(replies) >= self.config['reply_threshold']

    def update_reply_threshold(self, tweet, prefix):
        screen_names = self.get_screen_names(prefix)

        self.recent_replies().append({
            'created_at': arrow.utcnow(),
            'screen_names': screen_names,
        })

        self.log("Updated recent_replies: len = {}".format(len(self.recent_replies())))

    def get_screen_names(self, prefix):
        return [sn.replace('@', '') for sn in prefix.split()]

    def trim_recent_replies(self):
        len_before = len(self.recent_replies())
        now = arrow.utcnow()
        self.state['recent_replies'] = [
            r for r in self.recent_replies()
            if (now - r['created_at']).seconds < self.config['recent_replies_window']
        ]
        self.log("Trimmed recent_replies: {} -> {}".format(len_before, len(self.recent_replies())))

    def recent_replies(self):
        if 'recent_replies' not in self.state:
            self.state['recent_replies'] = []
        return self.state['recent_replies']

    def generate_gif(self, video_url, mosh_type=None):
        return Processor().mosh_url(video_url, mosh_type=mosh_type)

    def get_gif_video_url(self, tweet):
        url = self.get_gif_page_urls_climbing(tweet)
        if url is None:
            return None

        tweet_id = URL_PATTERN.match(url).group(2)

        self.log("Opening {}".format(url))
        html = urllib.urlopen(url).read()
        soup = BeautifulSoup(html)

        tag = soup.find('div', attrs={"data-tweet-id": tweet_id})
        if not tag:
            self.log("Couldn't find a div with data-tweet-id={} - giving up".format(repr(tweet_id)))
            return None

        match = re.search(r'https?://pbs\.twimg\.com/tweet_video_thumb/(.+)\.\w+', unicode(tag))
        if not match:
            self.log("Couldn't find a thumbnail URL - giving up")
            return None

        return "https://pbs.twimg.com/tweet_video/{}.mp4".format(match.group(1))

    def get_gif_page_urls_climbing(self, tweet):
        while True:
            url = self.get_gif_page_url(tweet)

            if url:
                return url

            if tweet.in_reply_to_status_id is None:
                break

            tweet = self.api.get_status(tweet.in_reply_to_status_id)

            # don't glitch yourself mate
            if tweet.author.id == self.id:
                self.log("Found my own tweet ({}) - stopping".format(self._tweet_url(tweet)))
                break

            self.log("Climbing up to status {}".format(self._tweet_url(tweet)))

    # We're looking for a media entity with a "http://twitter.com/.../photo/1" URL
    def get_gif_page_url(self, tweet):
        self.log("Getting GIF page URL for {}".format(self._tweet_url(tweet)))

        for media in tweet.entities.get('media', []):
            if URL_PATTERN.match(media['expanded_url']):
                self.log("Found link: {}".format(media['expanded_url']))
                return media['expanded_url']

        self.log("Tweet has no media entity with a matching URL - giving up")
        return None


def start_logging():
    stderr = logging.StreamHandler()
    stderr.setLevel(logging.DEBUG)
    stderr.setFormatter(logging.Formatter(fmt='%(levelname)8s: %(message)s'))

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(stderr)


if __name__ == '__main__':
    start_logging()
    bot = DataMosher()
    bot.run()
