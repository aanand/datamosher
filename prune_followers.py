from bot import DataMosher, start_logging
from tweepy import TweepError
from time import sleep

# Max user ids per lookup request
BATCH_SIZE = 100

# Time to wait between lookup requests
LOOKUP_DELAY = (15 * 60 / 300) + 1

# Time to wait between unfollow requests
UNFOLLOW_DELAY = 1

start_logging()

b = DataMosher()
friends = b.state['friends']

for i in range(0, len(friends), BATCH_SIZE):
    users = b.api.lookup_users(user_ids=friends[i:i+BATCH_SIZE])

    for user in users:
        try:
            if user.friends_count > b.config['autofollow_max_following']:
                b.log("unfollowing @{} (following {})".format(user.screen_name, user.friends_count))
                b.api.destroy_friendship(user.id)
                sleep(UNFOLLOW_DELAY)
        except TweepError as e:
            b._log_tweepy_error('Unable to unfollow user', e)

    sleep(LOOKUP_DELAY)
