import scrapy


class Inputs(scrapy.Item):
    accounts = scrapy.Field()
    historical_scrape_required = scrapy.Field()
    required_scrape_date = scrapy.Field()
    run_end_date = scrapy.Field()


class Profile(scrapy.Item):
    username = scrapy.Field()
    fullname = scrapy.Field()
    bio = scrapy.Field()
    followers = scrapy.Field()
    following = scrapy.Field()
    media_count = scrapy.Field()
    profile_pic = scrapy.Field()
    account_type = scrapy.Field()
    category = scrapy.Field()


class Post(scrapy.Item):
    # Fields inherited from Inputs
    accounts = scrapy.Field()
    input_url = scrapy.Field()
    date = scrapy.Field()
    post_text = scrapy.Field()
    post_id = scrapy.Field()
    likes = scrapy.Field()
    timestamp = scrapy.Field()
    number_of_comments = scrapy.Field()
    post_url = scrapy.Field()
    media_id = scrapy.Field()



class Reels(scrapy.Item):
    # Fields inherited from Inputs
    accounts = scrapy.Field()
    input_url = scrapy.Field()
    date = scrapy.Field()
    reel_text = scrapy.Field()
    reel_id = scrapy.Field()
    likes = scrapy.Field()
    timestamp = scrapy.Field()
    number_of_comments = scrapy.Field()
    reel_url = scrapy.Field()
    video_url = scrapy.Field()
    play_count = scrapy.Field()
    media_id = scrapy.Field()


class PostComment(scrapy.Item):
    post_id = scrapy.Field()
    media_id = scrapy.Field()
    number_of_comments = scrapy.Field()
    comment_index = scrapy.Field()
    comment_author = scrapy.Field()
    comment = scrapy.Field()
    comment_date = scrapy.Field()
    comment_created_at = scrapy.Field()
    comment_replies = scrapy.Field()


class ReelComment(scrapy.Item):
    reel_id = scrapy.Field()
    media_id = scrapy.Field()
    number_of_comments = scrapy.Field()
    comment_index = scrapy.Field()
    comment_author = scrapy.Field()
    comment = scrapy.Field()
    comment_date = scrapy.Field()
    comment_created_at = scrapy.Field()
    comment_replies = scrapy.Field()


class raw_InvalidInputUrl(scrapy.Item):
    # Fields inherited from Inputs
    accounts = scrapy.Field()
    historical_scrape_required = scrapy.Field()
    required_scrape_date = scrapy.Field()
    run_end_date = scrapy.Field()

    input_url = scrapy.Field()


class raw_PrivateProfile(scrapy.Item):
    # Fields inherited from Inputs
    accounts = scrapy.Field()
    historical_scrape_required = scrapy.Field()
    required_scrape_date = scrapy.Field()
    run_end_date = scrapy.Field()

    input_url = scrapy.Field()


class raw_exceeded_retry(scrapy.Item):
    request_data = scrapy.Field()
    input_url = scrapy.Field()