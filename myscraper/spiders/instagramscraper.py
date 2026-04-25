#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import json
import time
from copy import deepcopy
from datetime import datetime
from urllib.parse import parse_qs, urlencode

import scrapy
from scrapy.exceptions import IgnoreRequest

from .post import get_all_posts
from .comment import get_all_comments

from .request_utils import RequestUtilsIG
from .input_processor import InputProcessor

from myscraper.items import (
    Inputs,
    raw_InvalidInputUrl,
    raw_PrivateProfile,
    raw_exceeded_retry,
    PostComment,
    ReelComment,
    Post,
    Profile,
    Reels
)

MAX_RETRY = 9


def _retry_count(request):
    """Helper to get retry count from request meta (replaces response.request.retry)."""
    return request.meta.get("retry_count", 0)


class Spider(scrapy.Spider, InputProcessor, RequestUtilsIG):
    name = "instagram"
    start_urls = ["http://www.example.org"]
    allowed_domains = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.kwargs = kwargs
        self.data__req_comment = self.get___req_gen()

    def start_requests(self):
        self.logger.info("Processing the start requests")

        input_file = self.download_input_file()
        if not input_file:
            self.logger.warning("No input present.")
            return

        csv_input_generator = self.get_csv_input_generator(input_file)

        if not csv_input_generator:
            self.logger.warning("No input")
            return

        input_present = False
        for i, single_input in enumerate(csv_input_generator):
            print(f"the single input is {single_input}")
            if i >= 49:
                break
            single_input.pop("country", "")
            yield Inputs(**single_input)

            new_url = single_input.get("accounts", "")
            single_input["input_url"] = new_url
            input_present = True

            yield scrapy.Request(
                url=new_url,
                headers=self.accounts_headers,
                meta=single_input,
                callback=self.parse_profile_page,
                errback=self.handle_error,
            )

        if not input_present:
            self.logger.warning("No input")

    def handle_error(self, failure):
        request = failure.request
        retry_count = request.meta.get("retry_count", 0)
        self.logger.error(
            f"[NETWORK ERROR] url={request.url} retry={retry_count}/{MAX_RETRY} "
            f"error={failure.getErrorMessage()}"
        )
        if retry_count < MAX_RETRY:
            self.logger.info(f"[RETRY] Retrying {request.url} (attempt {retry_count + 1})")
            retry_req = request.copy()
            retry_req.meta["retry_count"] = retry_count + 1
            retry_req.dont_filter = True
            yield retry_req

    def _blocked_response(self, response):
        """Handle 403, 429, 500, 503 — retry with backoff up to MAX_RETRY times."""
        if response.status not in [403, 429, 500, 503]:
            return

        retry_count = response.meta.get("retry_count", 0)
        status = response.status

        if status == 429:
            wait = min(60 * (retry_count + 1), 300)  # 60s, 120s ... max 300s
            self.logger.warning(
                f"[RATE LIMITED 429] url={response.url} retry={retry_count}/{MAX_RETRY} "
                f"backing off {wait}s"
            )
        else:
            wait = 10 * (retry_count + 1)
            self.logger.warning(
                f"[BLOCKED {status}] url={response.url} retry={retry_count}/{MAX_RETRY} "
                f"backing off {wait}s"
            )

        if retry_count >= MAX_RETRY:
            self.logger.error(
                f"[GIVE UP] Max retries ({MAX_RETRY}) exceeded for {response.url} [{status}]"
            )
            raise IgnoreRequest(f"Max retries exceeded [{status}]")

        time.sleep(wait)
        retry_req = response.request.copy()
        retry_req.meta["retry_count"] = retry_count + 1
        retry_req.dont_filter = True
        raise IgnoreRequest(f"Retrying after {status} (attempt {retry_count + 1})")

    # ------------------------------------------------------------------ #
    # Profile
    # ------------------------------------------------------------------ #

    def parse_profile_details_page(self, response):
        """Parses profile details GraphQL JSON and yields a Profile item.
        Username is read from response.meta to avoid Scrapy callback arg limitations.
        """
        self._blocked_response(response)
        if response.status == 429:
            self.logger.warning("Profile details rate-limited (429) — skipping Profile item")
            return
        username = response.meta.get("username")
        try:
            profile_details = self.extract_instagram_profile_json(response)
            yield Profile(**profile_details)
            self.logger.info(f"[PROFILE DONE] username={profile_details.get('username')} followers={profile_details.get('followers')} posts={profile_details.get('media_count')}")
        except Exception as e:
            self.logger.error(f"[PROFILE ERROR] Failed to extract profile details: {e}")

    def parse_profile_page(self, response):
        with open("response_parse_profile_page.txt", "a") as f:
            f.write(response.text)
        self._blocked_response(response)

        meta = deepcopy(response.meta)
        print(f"the meta in profile page is :{meta}")
        self.logger.info(f"[PROFILE START] Scraping profile: {meta.get('accounts')}")

        if any(
            [
                response.status == 404,
                "the link you followed may be broken, or the page may have been removed"
                in response.text.lower(),
            ]
        ):
            yield raw_InvalidInputUrl(**meta)
            return
        if any(
            [
                "this account is private" in response.text.lower(),
                "follow to see their photos and videos" in response.text.lower(),
            ]
        ):
            yield raw_PrivateProfile(**meta)
            return

        try:
            csrf_token = self.parse_csrf_token(response)
            request_data = self.parse_lsd_jazoest(response)
            posts_req_args = self.request_params_profile_posts(response)
            profile_req_args = self.request_params_profile_details(
                response,
                meta.get("accounts"),
                next(self.data__req_comment),
                request_data,
                csrf_token,
            )
        except Exception as e:
            if _retry_count(response.request) > MAX_RETRY:
                yield raw_InvalidInputUrl(**meta)
                return
            raise Exception("Invalid Page") from e

        shared_meta = {**meta, "csrf_token": csrf_token, "request_data": request_data}

        print(f"Profile args : {profile_req_args}")
        yield scrapy.Request(
            **profile_req_args,
            meta={**shared_meta, "impersonate": "chrome", "username": meta.get("accounts")},
            callback=self.parse_profile_details_page,
            errback=self.handle_error,
        )

        # --- Posts (Reels are extracted inline from the same response) ---
        posts_req_args.pop("_variables", None)
        yield scrapy.Request(
            **posts_req_args,
            meta=shared_meta,
            callback=self.parse_profile_gql,
            errback=self.handle_error,
        )

    # ------------------------------------------------------------------ #
    # Meta cleanup
    # ------------------------------------------------------------------ #

    SPIDER_META_KEYS = {
        "accounts", "input_url", "historical_scrape_required",
        "required_scrape_date", "run_end_date",
        "csrf_token", "request_data",
        "post_id", "reel_id", "media_id",   # reel_id kept so ReelComment can read it
        "number_of_comments", "comment_index",
        "post_url", "reel_url",
        "timestamp", "date", "retry_count",
        "username",
        "profile_id",
        "comment_page",  # tracks comment pagination depth — max 2 pages
    }

    def _clean_meta(self, response):
        return {k: v for k, v in deepcopy(response.meta).items() if k in self.SPIDER_META_KEYS}

    # ------------------------------------------------------------------ #
    # Posts GQL
    # ------------------------------------------------------------------ #

    def parse_profile_gql(self, response):
        self._blocked_response(response)
        jdata = self._validate_json(response)
        meta = self._clean_meta(response)
        request_data = meta.pop("request_data", {})

        with open("response_parse_profile_gql.json", "a") as f:
            f.write(response.text)

        if (
            jdata.get("require_login")
            or "Please wait a few minutes before you try again" in response.text
        ):
            if _retry_count(response.request) > MAX_RETRY:
                yield raw_exceeded_retry(
                    **{
                        "input_url": meta.get("input_url"),
                        "request_data": json.dumps(
                            {
                                "url": response.url,
                                "headers": dict(response.request.headers),
                                "params": response.request.body.decode("utf-8", errors="ignore"),
                            }
                        ),
                    }
                )
                return
            else:
                raise Exception("Login Page")

        dict_keys = ["data", "user", "edge_owner_to_timeline_media", "edges"]
        edges = self.extract_edges(dict_keys, json_dict=jdata)

        if not edges:
            dict_keys = ["data", "user", "is_private"]
            if self.extract_edges(dict_keys, json_dict=jdata) is True:
                yield raw_PrivateProfile(**meta)
                return

        all_posts = get_all_posts(edges)
        self.logger.info(f"[POSTS] Found {len(all_posts)} posts for {meta.get('accounts')}")

        if not all_posts:
            if _retry_count(response.request) > 5:
                raise Exception("Empty Posts")
            yield raw_exceeded_retry(
                **{
                    "input_url": meta.get("input_url"),
                    "request_data": json.dumps(
                        {
                            "url": response.url,
                            "headers": dict(response.request.headers),
                            "params": response.request.body.decode("utf-8", errors="ignore"),
                        }
                    ),
                }
            )
            return

        # ---------------- POSTS ----------------
        for post in all_posts:
            account_url = meta.get("accounts", "")
            username = account_url.rstrip("/").split("/")[-1]
            post_data = {
                **post,
                "account": username,
                "post_url": f"{meta['input_url'].strip('/')}/p/{post['post_id']}/",
                "timestamp": str(int(datetime.timestamp(datetime.now()))),
            }
            try:
                clean_post_data = {k: v for k, v in post_data.items() if k in Post.fields}
                yield Post(**clean_post_data)
                self.logger.debug(f"[POST] post_id={post_data.get('post_id')} date={post_data.get('date')} likes={post_data.get('likes')} comments={post_data.get('number_of_comments')}")
            except KeyError as e:
                self.logger.error(f"Post item missing field: {e}")
                continue

            if post_data.get("number_of_comments"):
                yield from self.prepared_post_comment_request(post_data, meta, request_data)

        # ---------------- REELS (INLINE FIRST PAGE) ----------------
        yield from self._extract_reels_from_edges(edges, meta, request_data)

        # ---------------- ENSURE profile_id ----------------
        if not meta.get("profile_id"):
            for edge in edges:
                owner = edge.get("node", {}).get("owner", {})
                if owner.get("id"):
                    meta["profile_id"] = owner["id"]
                    break

        print(f"PROFILE ID (from edges): {meta.get('profile_id')}")

        # NOTE: Reels do NOT require pagination — they are extracted inline from the
        # same first-page edges above (_extract_reels_from_edges). The posts cursor
        # must NOT be reused to drive a separate reels pagination loop.

    # ------------------------------------------------------------------ #
    # Reels GQL
    # ------------------------------------------------------------------ #

    def _extract_reels_from_edges(self, edges, meta, request_data):
        """Yield Reels items (and reel comment requests) for any reel nodes in timeline edges.

        Called from parse_profile_gql only — reels live entirely on the first page of
        the timeline and do not require their own pagination.
        """
        for edge in edges:
            node = edge.get("node", {})
            product_type = node.get("product_type", "")
            is_video = node.get("is_video", False)


            is_reel = product_type == "clips" or (
                is_video and node.get("clips_music_attribution_info") is not None
            )
            if not is_reel:
                continue

            reel_id = node.get("shortcode", "") or node.get("code", "")
            media_id = node.get("id", "")
            n_comments = str(
                node.get("edge_media_to_comment", {}).get("count", "")
                or node.get("comment_count", "")
            )
            account_url = meta.get("accounts", "")
            username = account_url.rstrip("/").split("/")[-1]
            reel_data = {
                "account":username,
                "reel_id": reel_id,
                "media_id": media_id,
                "reel_url": f"{meta['input_url'].strip('/')}/reel/{reel_id}/",
                "date": str(datetime.utcfromtimestamp(
                    node.get("taken_at_timestamp", 0) or node.get("taken_at", 0)
                ).date()),
                "likes": str(
                    node.get("edge_liked_by", {}).get("count", "")
                    or node.get("edge_media_preview_like", {}).get("count", "")
                    or node.get("like_count", "")
                ),
                "reel_text": (
                    (node.get("edge_media_to_caption", {}).get("edges") or [{}])[0]
                    .get("node", {}).get("text", "")
                    or (node.get("caption") or {}).get("text", "")
                ),
                "number_of_comments": n_comments,
                "timestamp": str(int(datetime.timestamp(datetime.now()))),
                "video_url": node.get("video_url", ""),
                "play_count": str(
                    node.get("video_view_count", "")
                    or node.get("play_count", "")
                    or node.get("view_count", "")
                ),
            }
            self.logger.info(f"REEL reel_id={reel_id} date={reel_data['date']}")
            try:
                clean_reel_data = {k: v for k, v in reel_data.items() if k in Reels.fields}
                yield Reels(**clean_reel_data)
            except KeyError as e:
                self.logger.error(f"Reel item missing field: {e}")
                continue

            if n_comments and n_comments not in ("0", ""):
                yield from self.prepared_reel_comment_request(reel_data, request_data, meta)



    # ------------------------------------------------------------------ #
    # Comment requests
    # ------------------------------------------------------------------ #

    def prepared_comment_request(self, list_data, request_data):
        """Post comment request via comments endpoint v1."""
        req_args = self.get_request_params_comments(
            next(self.data__req_comment), list_data, request_data
        )
        yield scrapy.Request(
            **req_args,
            meta=list_data,
            callback=self.parse_post_comments,
            errback=self.handle_error,
        )

    def prepared_comment_request2(self, list_data, request_data):
        """Post comment request via comments endpoint v2."""
        req_args = self.get_request_params_comments2(
            next(self.data__req_comment), list_data, request_data
        )
        yield scrapy.Request(
            **req_args,
            meta=list_data,
            callback=self.parse_post_comments,
            errback=self.handle_error,
        )

    def prepared_post_comment_request(self, list_data, meta, request_data):
        request_meta = {
            "csrf_token": meta.get("csrf_token"),
            "input_url": meta.get("input_url"),
            "accounts": meta.get("accounts"),
            "media_id": list_data.get("media_id"),
            "post_id": list_data.get("post_id"),
            "number_of_comments": list_data.get("number_of_comments"),
            "post_url": list_data.get("post_url"),
            "comment_page": 1,
        }

        req_args = self.get_request_params_comments3(
            next(self.data__req_comment),
            request_meta,
            request_data
        )

        yield scrapy.Request(
            **req_args,
            meta=request_meta,
            callback=self.parse_post_comments,
            errback=self.handle_error,
        )

    def prepared_reel_comment_request(self, reel_data, request_data, meta):
        comment_meta = {
            **reel_data,
            "post_id": reel_data.get("reel_id"),
            "csrf_token": meta.get("csrf_token"),
            "input_url": meta.get("input_url"),
            "accounts": meta.get("accounts"),
            "comment_page": 1,
        }
        req_args = self.get_request_params_comments3(
            next(self.data__req_comment), comment_meta, request_data
        )
        yield scrapy.Request(
            **req_args,
            meta=comment_meta,
            callback=self.parse_reel_comments,
            errback=self.handle_error,
        )

    # ------------------------------------------------------------------ #
    # Shared comment parsing helper
    # ------------------------------------------------------------------ #

    def _extract_comment_edges(self, jdata):
        """Try both known edge paths and return the edges list (may be empty)."""
        edges = self.extract_edges(
            ["data", "xdt_shortcode_media", "edge_media_to_parent_comment", "edges"],
            json_dict=jdata,
        )
        if not edges:
            edges = self.extract_edges(
                ["data", "xdt_api__v1__media__media_id__comments__connection", "edges"],
                json_dict=jdata,
            )
        return edges

    def _handle_comment_rate_limit(self, response, jdata, meta):
        """Returns True and yields raw_exceeded_retry if rate-limited past MAX_RETRY."""
        if (
            jdata.get("require_login")
            or "Please wait a few minutes before you try again" in response.text
        ):
            if _retry_count(response.request) > MAX_RETRY:
                return True, raw_exceeded_retry(
                    **{
                        "input_url": meta.get("input_url"),
                        "request_data": json.dumps(
                            {
                                "url": response.url,
                                "headers": dict(response.request.headers),
                                "data": response.request.body.decode("utf-8", errors="ignore"),
                            }
                        ),
                    }
                )
            raise Exception("Login Page")
        return False, None

    def _build_next_comment_request(self, response, meta, callback):
        """Build and return the next paginated comment request, or None if no next page.
        Maximum 2 pages of comments per post/reel (page 1 = initial request, page 2 = one pagination).
        """
        current_page = meta.get("comment_page", 1)
        if current_page >= 2:
            self.logger.debug(f"Comment page limit reached (page {current_page}) — stopping")
            return None

        pagination_dict = self.get_pagination_dict_comments3(response)
        if not pagination_dict["has_next_page"] or not pagination_dict["end_cursor"]:
            return None

        request_args = {
            "method": response.request.method,
            "url": response.url,
            "headers": deepcopy(dict(response.request.headers)),
            "body": deepcopy(response.request.body),
        }
        next_request_args = self.get_next_request_data_comments3(request_args, pagination_dict)
        body_str = next_request_args["body"].decode("utf-8")
        qs = parse_qs(body_str, keep_blank_values=True)
        qs["__req"] = [next(self.data__req_comment)]
        next_request_args["body"] = urlencode({k: v[0] for k, v in qs.items()}).encode()

        meta["comment_page"] = current_page + 1
        return scrapy.Request(
            **next_request_args,
            meta=meta,
            callback=callback,
            errback=self.handle_error,
        )

    # ------------------------------------------------------------------ #
    # Post comments
    # ------------------------------------------------------------------ #

    def parse_post_comments(self, response):
        """Parse comments for a Post — yields PostComment items."""
        page = response.meta.get("comment_page", 1)
        self.logger.debug(f"[POST COMMENTS] Fetching page {page} for post_id={response.meta.get('post_id')}")
        self._blocked_response(response)
        jdata = self._validate_json(response)
        meta = self._clean_meta(response)

        rate_limited, error_item = self._handle_comment_rate_limit(response, jdata, meta)
        if rate_limited:
            yield error_item
            return

        edges = self._extract_comment_edges(jdata)
        comments = get_all_comments(edges)

        post_id = meta.get("post_id")
        media_id = meta.get("media_id")
        number_of_comments = meta.get("number_of_comments")
        meta["comment_index"] = meta.get("comment_index", 1)
        csrf_token = (
            response.request.headers.get("x-csrftoken", b"").decode()
            or response.request.headers.get("X-CSRFToken", b"").decode()
        )

        for comment in comments:
            yield PostComment(
                **{
                    "number_of_comments": number_of_comments,
                    "comment_index": str(meta["comment_index"]),
                    "post_id": post_id,
                    "media_id": media_id,
                    **comment,
                }
            )
            meta["comment_index"] += 1

        next_req = self._build_next_comment_request(response, meta, self.parse_post_comments)
        if next_req:
            yield next_req

    # ------------------------------------------------------------------ #
    # Reel comments
    # ------------------------------------------------------------------ #

    def parse_reel_comments(self, response):
        """Parse comments for a Reel — yields ReelComment items."""
        page = response.meta.get("comment_page", 1)
        self.logger.debug(f"[REEL COMMENTS] Fetching page {page} for reel_id={response.meta.get('reel_id')}")
        self._blocked_response(response)
        jdata = self._validate_json(response)
        meta = self._clean_meta(response)

        rate_limited, error_item = self._handle_comment_rate_limit(response, jdata, meta)
        if rate_limited:
            yield error_item
            return

        edges = self._extract_comment_edges(jdata)
        comments = get_all_comments(edges)

        reel_id = meta.get("reel_id")
        media_id = meta.get("media_id")
        number_of_comments = meta.get("number_of_comments")
        meta["comment_index"] = meta.get("comment_index", 1)
        csrf_token = (
            response.request.headers.get("x-csrftoken", b"").decode()
            or response.request.headers.get("X-CSRFToken", b"").decode()
        )

        for comment in comments:
            yield ReelComment(
                **{
                    "number_of_comments": number_of_comments,
                    "comment_index": str(meta["comment_index"]),
                    "reel_id": reel_id,
                    "media_id": media_id,
                    **comment,
                }
            )
            meta["comment_index"] += 1

        next_req = self._build_next_comment_request(response, meta, self.parse_reel_comments)
        if next_req:
            yield next_req

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def parse_lsd_jazoest(self, response):
        lsd = re.findall(r'"lsd":"([^"]*?)"', response.text)
        jazoest = re.findall(r'jazoest=(\d*?)[&"]', response.text)
        return {
            "lsd": lsd[0] if lsd else None,
            "jazoest": jazoest[0] if jazoest else None,
        }

    def parse_csrf_token(self, response):
        raw_token = re.findall(r'"csrf_token":"([^"]*?)"', response.text)
        csrf_token = raw_token and raw_token[0].replace("\\", "").replace('"', "")
        if csrf_token:
            return csrf_token

        raw_token = re.findall(
            r'"csrf_token\\":(.*),\\"viewer\\":', "".join(response.text.split())
        )
        csrf_token = raw_token and raw_token[0].replace("\\", "").replace('"', "")
        if csrf_token:
            return csrf_token

        raw_token = re.findall(
            r'"csrf_token":(.*),"viewer":', "".join(response.text.split())
        )
        csrf_token = raw_token and raw_token[0].replace("\\", "").replace('"', "")
        if csrf_token:
            return csrf_token

        self.logger.warning(
            f"Unable to find csrf token at profile page for {response.url} — all regex failed"
        )
        raise IgnoreRequest("Invalid response: no csrf token")

    def _validate_json(self, response):
        try:
            return response.json()
        except Exception:
            raise IgnoreRequest("Invalid JSON response")