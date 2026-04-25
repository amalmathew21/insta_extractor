import json
import random
from string import ascii_lowercase
from time import time

from .extract_content import ExtractContent


class GeneralRequestUtils(ExtractContent):
    def get___req_gen(self, limit=1261):
        while True:
            custom_base_characters = "123456789abcdefghijklmnopqrstuvwxyz"
            for i in range(2, limit):
                custom_base_representation = self.custom_base_generator(
                    i, custom_base_characters
                )
                yield custom_base_representation

    def custom_base_generator(self, number, base_characters):
        if not base_characters:
            raise ValueError("Base characters cannot be empty.")

        base = len(base_characters)

        if base < 2:
            raise ValueError("Base must be at least 2.")

        if number < 0:
            raise ValueError("Input number must be non-negative.")

        if number == 0:
            return base_characters[0]

        result = ""
        while number > 0:
            remainder = (number - 1) % base  # Adjusting for 1-based indexing
            result = base_characters[remainder] + result
            number = (number - 1) // base  # Adjusting for 1-based indexing

        return result

    def generate_number_string(self, digits: int) -> str:
        if digits <= 0:
            raise ValueError("Number of digits must be positive")

        first = str(random.randint(1, 9))
        rest = "".join(str(random.randint(0, 9)) for _ in range(digits - 1))
        return first + rest

    def create_random_id(self, ref_string="3wvpez:5n0c3r:bvxlzn"):
        random_id = ""
        for ch in ref_string:
            if ch.isnumeric():
                random_id += str(random.randint(1, 9))
            elif ch.isalpha():
                random_id += str(random.choice(list(ascii_lowercase)))
            else:
                random_id += ch
            return random_id

    def get_pagination_dict(self, response):
        dict_keys = ["data", "user", "edge_owner_to_timeline_media", "page_info"]
        page_info = self.nested_dict_extractor_without_key_error(
            json_obj=response.json(),
            dict_keys=dict_keys,
        )
        return {
            "has_next_page": page_info.get("has_next_page") is True,
            "end_cursor": page_info.get("end_cursor"),
        }

    def get_next_request_args(self, request_args, pagination_dict):
        from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
        parsed = urlparse(request_args["url"])
        qs = parse_qs(parsed.query, keep_blank_values=True)
        variables = json.loads(qs["variables"][0])
        variables["after"] = pagination_dict["end_cursor"]
        qs["variables"] = [json.dumps(variables)]
        new_query = urlencode({k: v[0] for k, v in qs.items()})
        request_args["url"] = urlunparse(parsed._replace(query=new_query))
        return request_args

    def get_pagination_dict_comments3(self, response):
        dict_keys = [
            "data",
            "xdt_api__v1__media__media_id__comments__connection",
            "page_info",
        ]
        page_info = self.nested_dict_extractor_without_key_error(
            json_obj=response.json(),
            dict_keys=dict_keys,
        )
        return {
            "has_next_page": page_info.get("has_next_page") is True,
            "end_cursor": page_info.get("end_cursor"),
        }

    def get_next_request_data_comments3(self, request_args, pagination_dict):
        from urllib.parse import parse_qs, urlencode
        body_str = request_args["body"].decode("utf-8")
        qs = parse_qs(body_str, keep_blank_values=True)
        variables = json.loads(qs["variables"][0])
        variables["after"] = pagination_dict["end_cursor"]
        qs["variables"] = [json.dumps(variables)]
        request_args["body"] = urlencode({k: v[0] for k, v in qs.items()}).encode()
        return request_args


class RequestUtilsIGPosts(GeneralRequestUtils):
    def request_params_profile_posts(self, response):
        variables = {
            "id": self.extract_profile_id(response.text),
            "after": None,
            "first": 12,
        }

        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:143.0) Gecko/20100101 Firefox/143.0",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.5",
            # 'Accept-Encoding': 'gzip, deflate, br, zstd',
            "X-Mid": self.create_random_id(
                ref_string="asai8viktjoqj46c9x1fdlcsu1ni9er61vjwddoy73lie1wzonxx"
            ),
            # 'X-CSRFToken': 'wVgh81DitO_2sB9E-eQa7H',
            "X-IG-App-ID": self.generate_number_string(15),
            "X-ASBD-ID": self.generate_number_string(6),
            "X-IG-WWW-Claim": "0",
            "X-Web-Session-ID": self.create_random_id(
                ref_string="3wvpez:5n0c3r:bvxlzn"
            ),
            "X-Requested-With": "XMLHttpRequest",
            "Connection": "keep-alive",
            # 'Referer': 'https://www.instagram.com/_sam_short/',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Priority": "u=0",
            "Pragma": "no-cache",
            "Cache-Control": "no-cache",
            # Requests doesn't support trailers
            # 'TE': 'trailers',
        }

        params = {
            "doc_id": "7950326061742207",
            "variables": json.dumps(variables),
        }

        base_url = "https://www.instagram.com/graphql/query/"
        url = f"{base_url}?{urlencode(params)}"

        return {
            "method": "GET",
            "url": url,
            "headers": headers,
            "_variables": variables,  # kept for pagination; not passed to scrapy.Request
        }

    def request_params_profile_reels_page(self, profile_id, after_cursor, csrf_token, username):
        """GET request to the same posts endpoint to fetch reel pages after the first.

        Uses the exact headers observed in the captured reels traffic (fixed x-ig-app-id,
        Chrome UA, x-ig-www-claim, x-csrftoken) so the paginated reel requests match
        what the browser sends.
        """
        variables = {
            "id": profile_id,
            "after": after_cursor,
            "first": 12,
        }

        headers = {
            "accept": "*/*",
            "accept-language": "en-GB,en-US;q=0.9,en;q=0.8,zh;q=0.7",
            "cache-control": "no-cache",
            "pragma": "no-cache",
            "priority": "u=1, i",
            "referer": f"https://www.instagram.com/{username.strip('/')}/",
            "sec-ch-prefers-color-scheme": "light",
            "sec-ch-ua": '"Not(A:Brand";v="8", "Chromium";v="144", "Google Chrome";v="144"',
            "sec-ch-ua-full-version-list": '"Not(A:Brand";v="8.0.0.0", "Chromium";v="144.0.7559.132", "Google Chrome";v="144.0.7559.132"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-model": '""',
            "sec-ch-ua-platform": '"Linux"',
            "sec-ch-ua-platform-version": '""',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
            "x-asbd-id": "359341",
            "x-csrftoken": csrf_token,
            "x-ig-app-id": "936619743392459",
            "x-ig-www-claim": "0",
            "x-requested-with": "XMLHttpRequest",
            "x-web-session-id": self.create_random_id(ref_string="oy8tnw:pn2904:gb4wq0"),
        }

        params = {
            "doc_id": "7950326061742207",
            "variables": json.dumps(variables),
        }

        url = f"https://www.instagram.com/graphql/query/?{urlencode(params)}"

        return {
            "method": "GET",
            "url": url,
            "headers": headers,
        }

    def request_params_profile_details(self, response, username, data__req, request_data, csrf_token):
        """POST request for profile details GraphQL query."""
        user_name = clean_username(username)

        headers = {
            'accept': '*/*',
            'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8,zh;q=0.7',
            'cache-control': 'no-cache',
            'content-type': 'application/x-www-form-urlencoded',
            'origin': 'https://www.instagram.com',
            'pragma': 'no-cache',
            'priority': 'u=1, i',
            'referer': f'https://www.instagram.com/{user_name}/',
            'sec-ch-prefers-color-scheme': 'light',
            'sec-ch-ua': '"Not(A:Brand";v="8", "Chromium";v="144", "Google Chrome";v="144"',
            'sec-ch-ua-full-version-list': '"Not(A:Brand";v="8.0.0.0", "Chromium";v="144.0.7559.132", "Google Chrome";v="144.0.7559.132"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-model': '""',
            'sec-ch-ua-platform': '"Linux"',
            'sec-ch-ua-platform-version': '""',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36',
            'x-asbd-id': '359341',
            'x-bloks-version-id': self.create_random_id(
                ref_string="f0fd53409d7667526e529854656fe20159af8b76db89f40c333e593b51a2ce10"
            ),
            'x-csrftoken': csrf_token,
            'x-fb-friendly-name': 'PolarisProfilePageContentQuery',
            'x-fb-lsd': request_data.get("lsd") or 'AdH12fobEes',
            'x-ig-app-id': self.generate_number_string(digits=15),
            'x-root-field-name': 'fetch__XDTUserDict',
        }

        variables = {
            "enable_integrity_filters": True,
            "id": self.extract_profile_id(response.text),
            "render_surface": "PROFILE",
            "__relay_internal__pv__PolarisCannesGuardianExperienceEnabledrelayprovider": True,
            "__relay_internal__pv__PolarisCASB976ProfileEnabledrelayprovider": False,
            "__relay_internal__pv__PolarisWebSchoolsEnabledrelayprovider": False,
            "__relay_internal__pv__PolarisRepostsConsumptionEnabledrelayprovider": False,
        }

        data = {
            "av": "0",
            "__d": "www",
            "__user": "0",
            "__a": "1",
            "__req": data__req,
            "__hs": "20553.HYP:instagram_web_pkg.2.1...0",
            "dpr": "1",
            "__ccg": "EXCELLENT",
            "__rev": "1037059972",
            "__s": "07xlh1:3qewwd:niajxr",
            "__hsi": "7627053137829730835",
            "__comet_req": "7",
            "lsd": request_data.get("lsd") or "AdH12fobEes",
            "jazoest": request_data.get("jazoest") or "2932",
            "__spin_r": "1027408144",
            "__spin_b": "trunk",
            "__spin_t": f"{time():.0f}",
            "fb_api_caller_class": "RelayModern",
            "fb_api_req_friendly_name": "PolarisProfilePageContentQuery",
            "server_timestamps": "true",
            "variables": json.dumps(variables),
            "doc_id": "25941171822250795",
        }

        return {
            "method": "POST",
            "url": "https://www.instagram.com/graphql/query/",
            "headers": headers,
            "body": urlencode(data).encode(),
        }


class RequestUtilsIGComments(GeneralRequestUtils):
    def get_request_params_comments(self, data__req, request_meta, request_data):
        csrf_token = request_meta["csrf_token"]
        post_id = request_meta["post_id"]
        headers = {
            "accept": "*/*",
            "accept-language": "en-GB,en;q=0.9",
            "content-type": "application/x-www-form-urlencoded",
            "origin": "https://www.instagram.com",
            "priority": "u=1, i",
            "sec-ch-prefers-color-scheme": "light",
            "sec-ch-ua": '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"',
            # 'sec-ch-ua-full-version-list': '"Chromium";v="134.0.6998.35", "Not:A-Brand";v="24.0.0.0", "Google Chrome";v="134.0.6998.35"',
            "sec-ch-ua-mobile": "?0",
            # 'sec-ch-ua-model': '""',
            "sec-ch-ua-platform": '"Linux"',
            # 'sec-ch-ua-platform-version': '"6.8.0"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
            "x-asbd-id": "359341",
            "x-bloks-version-id": self.create_random_id(
                ref_string="446750d9733aca29094b1f0c8494a768d5742385af7ba20c3e67c9afb91391d8"
            ),
            "x-csrftoken": csrf_token,
            "x-fb-friendly-name": "PolarisPostActionLoadPostQueryQuery",
            "x-ig-app-id": self.generate_number_string(digits=15),
            "x-root-field-name": "xdt_shortcode_media",
        }
        variables = {
            "shortcode": str(post_id),
            "fetch_tagged_user_count": None,
            "hoisted_comment_id": None,
            "hoisted_reply_id": None,
        }
        data = {
            "av": "0",
            "__d": "www",
            "__user": "0",
            "__a": "1",
            "__req": data__req,
            "dpr": "1",
            "__ccg": "UNKNOWN",
            "__rev": "1017179990",
            "__comet_req": "15",
            "lsd": request_data.get("lsd") or "AdH12fobEes",
            "jazoest": request_data.get("jazoest") or "2932",
            "__spin_r": "1017179990",
            "__spin_b": "trunk",
            "__spin_t": f"{time():.0f}",
            "fb_api_caller_class": "RelayModern",
            "fb_api_req_friendly_name": "PolarisPostActionLoadPostQueryQuery",
            "variables": json.dumps(variables),
            "server_timestamps": "true",
            "doc_id": "8845758582119845",
        }
        return {
            "method": "POST",
            "url": "https://www.instagram.com/graphql/query/",
            "headers": headers,
            "body": urlencode(data).encode(),
        }

    def get_request_params_comments2(self, data__req, request_meta, request_data):
        csrf_token = request_meta["csrf_token"]
        media_id = request_meta["media_id"]
        headers = {
            "accept": "*/*",
            "accept-language": "en-GB,en;q=0.9",
            "cache-control": "no-cache",
            "content-type": "application/x-www-form-urlencoded",
            "origin": "https://www.instagram.com",
            "pragma": "no-cache",
            "priority": "u=1, i",
            "referer": "https://www.instagram.com/rachinravindra/p/DN2t780WMww/",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Linux"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36",
            "x-asbd-id": "359341",
            "x-bloks-version-id": self.create_random_id(
                ref_string="64f02abc184fb0d9135db12e85e451a3be71c64f7231c320a09e7df0ef1bdf6d"
            ),
            "x-csrftoken": csrf_token,
            "x-fb-friendly-name": "PolarisPostCommentsPaginationQuery",
            "x-fb-lsd": "AdEyBwE1sGs",
            "x-ig-app-id": self.generate_number_string(digits=15),
            "x-root-field-name": "xdt_api__v1__media__media_id__comments__connection",
        }

        variables = {
            "after": None,
            "before": None,
            "first": 10,
            "last": None,
            "media_id": media_id,
            "sort_order": "popular",
            "__relay_internal__pv__PolarisIsLoggedInrelayprovider": True,
        }

        data = {
            "av": "0",
            "__d": "www",
            "__user": "0",
            "__a": "1",
            "__req": data__req,
            "dpr": "1",
            "__ccg": "EXCELLENT",
            "__rev": "1027408144",
            "__comet_req": "15",
            "lsd": request_data.get("lsd") or "AdH12fobEes",
            "jazoest": request_data.get("jazoest") or "2932",
            "__spin_r": "1027408144",
            "__spin_b": "trunk",
            "__spin_t": f"{time():.0f}",
            "__crn": "comet.igweb.PolarisLoggedOutDesktopPostRouteNext",
            "fb_api_caller_class": "RelayModern",
            "fb_api_req_friendly_name": "PolarisPostCommentsPaginationQuery",
            "variables": json.dumps(variables),
            "server_timestamps": "true",
            "doc_id": "9810871498999190",
        }

        return {
            "method": "POST",
            "url": "https://www.instagram.com/graphql/query/",
            "headers": headers,
            "body": urlencode(data).encode(),
        }

    def get_request_params_comments3(self, data__req, request_meta, request_data):
        csrf_token = request_meta["csrf_token"]
        media_id = request_meta["media_id"]

        headers = {
            "accept": "*/*",
            "accept-language": "en-GB,en;q=0.9",
            "cache-control": "no-cache",
            "content-type": "application/x-www-form-urlencoded",
            "origin": "https://www.instagram.com",
            "pragma": "no-cache",
            "priority": "u=1, i",
            "referer": "https://www.instagram.com/superrugbynz/p/C4q0UpKBAap/",
            "sec-ch-prefers-color-scheme": "light",
            "sec-ch-ua": '"Chromium";v="146", "Not-A.Brand";v="24", "Google Chrome";v="146"',
            "sec-ch-ua-full-version-list": '"Chromium";v="146.0.7680.80", "Not-A.Brand";v="24.0.0.0", "Google Chrome";v="146.0.7680.80"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-model": '""',
            "sec-ch-ua-platform": '"Linux"',
            "sec-ch-ua-platform-version": '""',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
            "x-asbd-id": "359341",
            "x-bloks-version-id": self.create_random_id(
                ref_string="f0fd53409d7667526e529854656fe20159af8b76db89f40c333e593b51a2ce10"
            ),
            "x-csrftoken": csrf_token,
            "x-fb-friendly-name": "PolarisPostCommentsPaginationQuery",
            "x-fb-lsd": request_data.get("lsd") or "AdH12fobEes",
            "x-ig-app-id": self.generate_number_string(digits=15),
            "x-root-field-name": "xdt_api__v1__media__media_id__comments__connection",
        }

        variables = {
            "after": None,
            "before": None,
            "first": 10,
            "last": None,
            "media_id": media_id,
            "sort_order": "popular",
            "__relay_internal__pv__PolarisIsLoggedInrelayprovider": False,
        }

        data = {
            "av": "0",
            "__d": "www",
            "__user": "0",
            "__a": "1",
            "__req": data__req,
            "__hs": "20553.HYP:instagram_web_pkg.2.1...0",
            "dpr": "1",
            "__ccg": "EXCELLENT",
            "__rev": "1037059972",
            "__s": "07xlh1:3qewwd:niajxr",
            "__hsi": "7627053137829730835",
            "__comet_req": "7",
            "lsd": request_data.get("lsd") or "AdH12fobEes",
            "jazoest": request_data.get("jazoest") or "2932",
            "__spin_r": "1027408144",
            "__spin_b": "trunk",
            "__spin_t": f"{time():.0f}",
            "__crn": "comet.igweb.PolarisLoggedOutDesktopPostRouteNext",
            "fb_api_caller_class": "RelayModern",
            "fb_api_req_friendly_name": "PolarisPostCommentsPaginationQuery",
            "server_timestamps": "true",
            "variables": json.dumps(variables),
            "doc_id": "26224338453892885",
        }

        return {
            "method": "POST",
            "url": "https://www.instagram.com/graphql/query/",
            "headers": headers,
            "body": urlencode(data).encode(),
        }


class RequestUtilsIG(RequestUtilsIGPosts, RequestUtilsIGComments):
    accounts_headers = {
        "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:143.0) Gecko/20100101 Firefox/143.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        # 'Accept-Encoding': 'gzip, deflate, br, zstd',
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Priority": "u=0, i",
        "Pragma": "no-cache",
        "Cache-Control": "no-cache",
        # Requests doesn't support trailers
        # 'TE': 'trailers',
    }

from urllib.parse import urlencode, urlparse

def clean_username(username):
    # If it's a full URL, extract the username
    if username.startswith("http"):
        path = urlparse(username).path
        return path.strip("/").split("/")[0]
    return username.strip("/")