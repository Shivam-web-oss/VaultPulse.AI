"""Source access policy (doc §15).

Only permitted sources may be accessed, respecting terms, access
restrictions, and rate limits.

Phase D: the allow-list holds real domains with explicit permission to be
collected (public sandboxes and official keyless APIs). Each domain's
robots.txt is fetched once and cached per process; robots disallows are
enforced for all user agents. A per-domain token bucket (refilled lazily)
enforces the rate limit table below. HTML page fetches go through
app.tools.fetcher, which calls check_url() before every request.
"""

import logging
import os
import threading
import time
import urllib.robotparser
from dataclasses import dataclass
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

USER_AGENT = os.getenv("COLLECTOR_USER_AGENT", "VaultPulse-Collector/1.0 (+https://vaultpulse.ai/bot)")

# Domains explicitly permitted for collection. Every entry is either an
# official keyless API intended for programmatic use or a site that invites
# scraping (sandbox / permissive robots). Do not add domains without checking
# robots.txt and terms of service.
PERMITTED_SOURCES: dict[str, dict] = {
    "books.toscrape.com": {
        "name": "Books To Scrape (sandbox)",
        "kind": "html",
        "entity": "product",
        "rate_limit_rps": 0.5,  # 1 request every 2 seconds
    },
    "www.arbeitnow.com": {
        "name": "Arbeitnow Job Board API",
        "kind": "api",
        "entity": "job",
        "rate_limit_rps": 0.5,
    },
    "hn.algolia.com": {
        "name": "Hacker News Search (Algolia API)",
        "kind": "api",
        "entity": "record",
        "rate_limit_rps": 1.0,
    },
}

# robots.txt handling

_ROBOTS_TTL = 3600  # seconds before a cached robots.txt is refetched
_ROBOTS_TIMEOUT = 5.0
_ROBOTS_MAX_BYTES = 256 * 1024

_ROBOTS_CACHE: dict[str, tuple[float, urllib.robotparser.RobotFileParser | None]] = {}
_ROBOTS_LOCK = threading.Lock()

# Token buckets keyed by domain.
_BUCKETS: dict[str, "_TokenBucket"] = {}
_BUCKETS_LOCK = threading.Lock()


@dataclass
class _TokenBucket:
    rate: float  # tokens per second
    capacity: int
    tokens: float
    updated_at: float

    def take(self, amount: float = 1.0) -> float:
        """Try to take `amount` tokens; return seconds to wait if unavailable (0 = ok)."""
        now = time.monotonic()
        elapsed = now - self.updated_at
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        self.updated_at = now
        if self.tokens >= amount:
            self.tokens -= amount
            return 0.0
        return (amount - self.tokens) / self.rate


def _bucket_for(domain: str) -> _TokenBucket:
    with _BUCKETS_LOCK:
        bucket = _BUCKETS.get(domain)
        if bucket is None:
            rate = float(PERMITTED_SOURCES.get(domain, {}).get("rate_limit_rps", 0.5))
            bucket = _TokenBucket(rate=rate, capacity=5, tokens=5, updated_at=time.monotonic())
            _BUCKETS[domain] = bucket
        return bucket


def domain_of(source_or_url: str) -> str:
    """Extract the hostname from a source name or URL; '' if unparseable."""
    value = source_or_url.strip()
    if not value:
        return ""
    if "://" not in value:
        value = f"https://{value}"
    try:
        host = urlparse(value).hostname
    except ValueError:
        return ""
    return (host or "").lower()


def is_permitted(source: str) -> bool:
    """True if the domain (or URL's domain) is on the explicit allow-list."""
    return domain_of(source) in PERMITTED_SOURCES


def rate_limit_delay(domain: str) -> float:
    """Consume one token for `domain`; return seconds the caller must sleep first (0 = go now)."""
    if domain not in PERMITTED_SOURCES:
        return float("inf")  # never permitted: an infinite wait, callers treat as refusal
    return _bucket_for(domain).take()


def _load_robots(domain: str):
    """Fetch and parse robots.txt for a domain once per TTL; None if unavailable."""
    now = time.monotonic()
    with _ROBOTS_LOCK:
        cached = _ROBOTS_CACHE.get(domain)
        if cached and now - cached[0] < _ROBOTS_TTL:
            return cached[1]

    parser = urllib.robotparser.RobotFileParser()
    parser.set_url(f"https://{domain}/robots.txt")
    try:
        import httpx  # local import avoids a module-level cycle with app.tools.fetcher

        response = httpx.get(
            f"https://{domain}/robots.txt",
            headers={"User-Agent": USER_AGENT},
            timeout=_ROBOTS_TIMEOUT,
            follow_redirects=True,
        )
        if response.status_code == 200:
            parser.parse(response.text[:_ROBOTS_MAX_BYTES].splitlines())
        elif response.status_code in (401, 403):
            parser.allow_all = False  # unreachable robots.txt means do not fetch
        else:
            parser.allow_all = True  # 404 / others: no robots rules published
    except Exception as error:  # noqa: BLE001 - robots must never break collection
        logger.warning("robots.fetch_failed domain=%s error=%s", domain, error)
        parser.allow_all = True

    with _ROBOTS_LOCK:
        _ROBOTS_CACHE[domain] = (now, parser)
    return parser


def robots_allowed(url: str) -> bool:
    """True if robots.txt for the URL's domain permits USER_AGENT to fetch it."""
    domain = domain_of(url)
    if not domain:
        return False
    parser = _load_robots(domain)
    if parser is None:
        return False
    return parser.can_fetch(USER_AGENT, url)


def check_url(url: str) -> bool:
    """Full admission check for a page fetch: allow-list + robots.txt."""
    if not is_permitted(url):
        return False
    return robots_allowed(url)


def source_name(domain: str) -> str:
    return str(PERMITTED_SOURCES.get(domain, {}).get("name", domain))


def source_kind(domain: str) -> str:
    return str(PERMITTED_SOURCES.get(domain, {}).get("kind", "html"))


def permitted_domains_for_entity(entity: str) -> list[str]:
    """Domains on the allow-list that serve the given entity type."""
    return [d for d, meta in PERMITTED_SOURCES.items() if meta.get("entity") == entity]
