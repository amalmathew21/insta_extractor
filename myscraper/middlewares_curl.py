"""
CurlCffiMiddleware
==================
Replaces Scrapy's default downloader for requests tagged with
    meta={"impersonate": "chrome"}   (or any curl_cffi browser string)

This bypasses Instagram's TLS fingerprint detection, which blocks
Python/Twisted's TLS handshake with a 429.

INSTALL:
    pip install curl_cffi

ENABLE in settings.py:
    DOWNLOADER_MIDDLEWARES = {
        "myscraper.middlewares_curl.CurlCffiMiddleware": 585,
    }

USAGE — tag any Request that needs TLS impersonation:
    scrapy.Request(url, meta={"impersonate": "chrome"}, ...)

Requests WITHOUT the meta key pass through normally via Scrapy's
default downloader, so posts/comments (which already work) are unaffected.
"""

import logging
from io import BytesIO

from scrapy import signals
from scrapy.http import HtmlResponse, TextResponse, Response
from scrapy.exceptions import NotConfigured

logger = logging.getLogger(__name__)

try:
    from curl_cffi import requests as curl_requests
    CURL_CFFI_AVAILABLE = True
except ImportError:
    CURL_CFFI_AVAILABLE = False


class CurlCffiMiddleware:
    """Downloader middleware that uses curl_cffi for TLS-impersonated requests."""

    @classmethod
    def from_crawler(cls, crawler):
        if not CURL_CFFI_AVAILABLE:
            raise NotConfigured("curl_cffi is not installed. Run: pip install curl_cffi")
        mw = cls()
        crawler.signals.connect(mw.spider_opened, signal=signals.spider_opened)
        return mw

    def spider_opened(self, spider):
        logger.info("CurlCffiMiddleware enabled — TLS impersonation active")

    def process_request(self, request, spider):
        impersonate = request.meta.get("impersonate")
        if not impersonate:
            return None  # Let Scrapy handle it normally

        logger.debug(f"curl_cffi [{impersonate}] → {request.url}")

        try:
            resp = curl_requests.request(
                method=request.method,
                url=request.url,
                headers=dict(request.headers.to_unicode_dict()),
                data=request.body or None,
                impersonate=impersonate,
                timeout=30,
                allow_redirects=True,
            )
        except Exception as e:
            logger.error(f"curl_cffi request failed for {request.url}: {e}")
            raise

        # Build a Scrapy Response from the curl_cffi response
        content_type = resp.headers.get("content-type", "")
        encoding = "utf-8"

        if "json" in content_type or "javascript" in content_type:
            response_cls = TextResponse
        elif "html" in content_type:
            response_cls = HtmlResponse
        else:
            response_cls = Response

        scrapy_response = response_cls(
            url=resp.url,
            status=resp.status_code,
            headers=dict(resp.headers),
            body=resp.content,
            encoding=encoding,
            request=request,
        )
        return scrapy_response