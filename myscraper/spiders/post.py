import pytz
from datetime import datetime


def clean_data(string):
    if not isinstance(string, str):
        return string

    return " ".join(string.split()).strip()


def formatted_date_tz_converted(timestamp, output_tz="Pacific/Auckland"):
    if not timestamp:
        return
    TZ = pytz.timezone(output_tz)
    utc_datetime = datetime.utcfromtimestamp(int(timestamp))
    TZ_datetime = pytz.utc.localize(utc_datetime).astimezone(TZ)
    return TZ_datetime.strftime("%Y-%m-%d")


def get_post(post):

    media_id = post.get("node", {}).get("id")
    edge_media_preview_like = post.get("node", {}).get("edge_media_preview_like", {})
    likes = edge_media_preview_like.get("count")
    edge_media_to_comment = post.get("node", {}).get("edge_media_to_comment", {})
    number_of_comments = edge_media_to_comment.get("count")

    edge_media_to_caption = post.get("node", {}).get("edge_media_to_caption", {})
    post_text = (
        (
            edge_media_to_caption.get("edges") or [{}]
        )[0].get("node") or {}).get("text") or None

    shortcode = post.get("node", {}).get("shortcode")
    taken_at_timestamp = post.get("node", {}).get("taken_at_timestamp")

    if isinstance(likes, int) and likes < 0:
        likes = None
    final_return_data = {
        "date": formatted_date_tz_converted(taken_at_timestamp),
        "post_text": post_text,
        "post_id": str(shortcode) if shortcode else None,
        "likes": str(likes) if likes else None,
        "timestamp": str(taken_at_timestamp),
        "number_of_comments": str(number_of_comments) if number_of_comments else None,
        "media_id": str(media_id),
    }
    return {k: clean_data(v) for k, v in final_return_data.items()}


def get_all_posts(edges):
    parsed_posts_list = []

    for post in edges:
        parsed_post = get_post(post)
        parsed_posts_list.append(parsed_post)

    return parsed_posts_list
