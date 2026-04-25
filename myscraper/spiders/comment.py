import pytz
from datetime import datetime

def formatted_date_tz_converted(timestamp, output_tz="Pacific/Auckland"):
    if not timestamp:
        return
    TZ = pytz.timezone(output_tz)
    utc_datetime = datetime.utcfromtimestamp(int(timestamp))
    TZ_datetime = pytz.utc.localize(utc_datetime).astimezone(TZ)
    return TZ_datetime.strftime("%Y-%m-%d")


def clean_data(string):
    if not isinstance(string, str):
        return string

    return " ".join(string.split()).strip()


def nested_dict_extract_temp(json_obj, dict_keys):
    """
    Function to avoid repetitive .get().get() calls
    To be removed and replaced with nested_dict_extract.
    """
    temp_dict = json_obj
    for key in dict_keys:
        temp_dict = temp_dict.get(key, {}) or {}
    return temp_dict


def get_all_comments(edges):
    """
    Get all posts from json_obj
    """
    parsed_comments_list = []

    for comment in edges:
        parsed_comment = get_comment(comment)
        parsed_comments_list.append(parsed_comment)

    return parsed_comments_list


def get_comment(edge):
    user = edge.get("node", {}).get("owner") or edge.get("node", {}).get("user")
    author = user.get("username")
    text = edge.get("node", {}).get("text")
    created_at = edge.get("node", {}).get("created_at")
    replies_edges = nested_dict_extract_temp(
        edge.get("node", {}) or {}, ['edge_threaded_comments', 'edges'])

    reply_text_list = []
    for reply_edge in replies_edges:
        reply_text = nested_dict_extract_temp(reply_edge, ['node', 'text']) or None
        if not isinstance(reply_text, str):
            reply_text = None
        if not reply_text:
            continue

        reply_text_list.append(reply_text)

    comment_data = {
        "comment_author": author,
        "comment": text,
        "comment_date": formatted_date_tz_converted(created_at),
        "comment_created_at": str(created_at),
        "comment_replies": " | ".join(reply_text_list) or None
    }

    return {k: clean_data(v) for k, v in comment_data.items()}
