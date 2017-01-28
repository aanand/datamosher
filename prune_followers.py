from bot import DataMosher, start_logging

start_logging()

b = DataMosher()

for friend_id in b.state['friends']:
    user = b.api.get_user(friend_id)
    if user.friends_count > b.config['autofollow_max_following']:
        b.log("unfollowing @{} (following {})".format(user.screen_name, user.friends_count))
        b.api.destroy_friendship(friend_id)
    else:
        b.log("@{} is cool (following {})".format(user.screen_name, user.friends_count))
