"""Policy-enforced HTTP client (Phase D).

Every outbound fetch in the collection pipeline goes through fetch_url().
It refuses non-permitted domains, honors robots.txt, waits for the
per-domain token bucket, and returns structured results with real
retrieval timestamps so ProvenanceEntry.sourceUrl / retrievedAt reflect
actual HTTP responses.
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

import httpx

from app.tools.source_policy import (
    USER_AGENT,
    check_url,
    domain_of,
    is_permitted,
    rate_limit_delay,
    source_kind,
    source_name,
)

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 15.0
MAX_REDIRECTS = 3

_BROWSERISH_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
}


@dataclass
class FetchResult:
    url: str
    status: int
    content: str
    content_type: str
    retrieved_at: datetime
    source_name: str
    source_kind: str
    domain: str
    error: str = ""
    elapsed_ms: int = 0
    headers: dict = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.status == 200 and not self.error


def fetch_url(url: str, *, timeout: float = DEFAULT_TIMEOUT) -> FetchResult:
    """Fetch one URL under the full source policy.

    Returns a FetchResult with status 0 and an error message when the
    policy or the network refuses the fetch. Never raises.
    """
    domain = domain_of(url)
    started = time.monotonic()
    retrieved_at = datetime.now(timezone.utc)

    if not domain:
        return _refused(url, retrieved_at, "unparseable URL")
    if not is_permitted(domain):
        logger.info("fetch.refused_not_permitted domain=%s url=%s", domain, url)
        return _refused(url, retrieved_at, "domain not permitted")
    if not check_url(url):
        logger.info("fetch.refused_robots domain=%s url=%s", domain, url)
        return _refused(url, retrieved_at, "robots.txt disallows this path")

    delay = rate_limit_delay(domain)
    if delay == float("inf"):
        return _refused(url, retrieved_at, "domain not permitted")
    if delay > 0:
        logger.debug("fetch.rate_limit_wait domain=%s wait=%.2fs", domain, delay)
        time.sleep(min(delay, 60.0))

    try:
        with httpx.Client(
            headers=_BROWSERISH_HEADERS,
            timeout=timeout,
            follow_redirects=True,
            max_redirects=MAX_REDIRECTS,
        ) as client:
            response = client.get(url)
        retrieved_at = datetime.now(timezone.utc)
        elapsed = int((time.monotonic() - started) * 1000)
        content_type = response.headers.get("content-type", "")
        # API sources return JSON; keep raw text and let callers decode.
        content = response.text
        logger.info(
            "fetch.ok domain=%s status=%s bytes=%s elapsed_ms=%s",
            domain, response.status_code, len(content), elapsed,
        )
        return FetchResult(
            url=str(response.url),
            status=response.status_code,
            content=content,
            content_type=content_type,
            retrieved_at=retrieved_at,
            source_name=source_name(domain),
            source_kind=source_kind(domain),
            domain=domain,
            elapsed_ms=elapsed,
            headers=dict(response.headers),
        )
    except Exception as error:  # noqa: BLE001 - fetch must never break collection
        logger.warning("fetch.failed domain=%s url=%s error=%s", domain, url, error)
        return _refused(url, datetime.now(timezone.utc), f"fetch failed: {error}")


def _refused(url: str, retrieved_at: datetime, error: str) -> FetchResult:
    domain = domain_of(url)
    return FetchResult(
        url=url,
        status=0,
        content="",
        content_type="",
        retrieved_at=retrieved_at,
        source_name=source_name(domain),
        source_kind=source_kind(domain),
        domain=domain,
        error=error,
    )


def fetch_json(url: str, *, timeout: float = DEFAULT_TIMEOUT) -> tuple:
    """Convenience wrapper: fetch and parse JSON. Returns (data, FetchResult)."""
    result = fetch_url(url, timeout=timeout)
    if not result.ok:
        return None, result
    try:
        import json

        return json.loads(result.content), result
    except (ValueError, TypeError) as error:
        result.error = f"invalid JSON: {error}"
        return None, result
