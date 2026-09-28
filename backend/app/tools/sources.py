"""Permitted source adapters (Phase D).

Each adapter turns a candidate query + offset into real candidate URLs and
extracts records from the source's real response shape. All network I/O goes
through app.tools.fetcher, so robots.txt and per-domain rate limits always
apply.

Allow-listed sources and their roles:
- books.toscrape.com   static HTML catalogue, product entity; candidates are
                       catalogue page URLs, extraction uses CSS selectors.
- www.arbeitnow.com    keyless JSON job-board API, job entity; one candidate
                       page URL per fetch, extraction walks the JSON envelope.
- hn.algolia.com       official HN Search API, generic record entity; the
                       search response itself carries the records.

Record shapes match FIELD_TEMPLATES in app.ai.requirement_analyzer so the
normalize/validate nodes can process them unchanged.
"""

import logging
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import quote_plus, urljoin

from bs4 import BeautifulSoup

from app.tools import fetcher, source_policy

logger = logging.getLogger(__name__)

BOOKS_CATALOGUE = "https://books.toscrape.com/catalogue/page-{page}.html"
ARBEITNOW_API = "https://www.arbeitnow.com/api/job-board-api"
HN_SEARCH_API = "https://hn.algolia.com/api/v1/search"

_BOOKS_PAGE_SIZE = 20
_HN_PAGE_SIZE = 100
ARBEITNOW_PAGE_SIZE = 325  # records returned per API page (verified 2026-09)
_HN_CACHE_TTL = 60  # seconds; search + extract in one round share one response
_HN_CACHE: dict[str, tuple[float, list]] = {}

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _hn_hits(query: str, page: int = 1) -> list[dict]:
    """HN search hits with a short TTL cache so search+extract share one fetch."""
    key = f"{query}|{page}"
    now = time.monotonic()
    cached = _HN_CACHE.get(key)
    if cached and now - cached[0] < _HN_CACHE_TTL:
        return cached[1]
    data, _result = fetcher.fetch_json(
        f"{HN_SEARCH_API}?query={quote_plus(query or 'news')}&hitsPerPage={_HN_PAGE_SIZE}&page={page}&tags=story"
    )
    hits = data.get("hits", []) if isinstance(data, dict) else []
    _HN_CACHE[key] = (now, hits)
    return hits

_STAR_WORDS = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}


@dataclass
class Candidate:
    """A concrete URL a PageExtractionTool round can fetch."""

    url: str
    label: str = ""
    offset_hint: int = 0  # for API/listing sources: page number or record offset


# -- candidate discovery (search phase) ---------------------------------------


def find_candidates(entity: str, query: str, offset: int, take: int) -> list[Candidate]:
    """Discover candidate URLs for an entity from the permitted sources."""
    if entity == "product":
        # Book catalogue pages hold ~20 records each; record offset -> page number.
        page = (offset // 20) + 1
        return [Candidate(url=BOOKS_CATALOGUE.format(page=page), label=query or "catalogue", offset_hint=offset)]
    if entity == "job":
        # One API page returns ~325 jobs; every round fetches page 1 unless a
        # larger offset is planned explicitly.
        page = (offset // 100) + 1
        return [Candidate(url=ARBEITNOW_API + (f"?page={page}" if page > 1 else ""), label=query, offset_hint=offset)]
    # record / generic web index: the search API response is itself the payload.
    hits = _hn_hits(query or "news", page=1)
    records = extract_hn_hits(hits[offset:])
    return [
        Candidate(
            url=record["url"],
            label=record["title"],
            offset_hint=offset + index,
        )
        for index, record in enumerate(records)
    ]


def extract_from_url(url: str, entity: str) -> list[dict]:
    """Fetch one candidate URL under policy and extract records from it."""
    result = fetcher.fetch_url(url)
    if not result.ok:
        logger.info("source.extract_skipped url=%s error=%s", url, result.error)
        return []
    if result.source_kind == "api" or "json" in result.content_type:
        import json

        try:
            payload = json.loads(result.content)
        except ValueError:
            logger.info("source.json_decode_failed url=%s", url)
            return []
        if "arbeitnow" in result.domain:
            return _extract_arbeitnow(payload, result)
        return []
    soup = BeautifulSoup(result.content, "html.parser")
    if "books.toscrape.com" in result.domain:
        return _extract_books(soup, result)
    return []


# -- Books to Scrape (product entity, HTML selectors) --------------------------


def _extract_books(soup: BeautifulSoup, result: fetcher.FetchResult) -> list[dict]:
    records = []
    for card in soup.select("article.product_pod"):
        title_tag = card.select_one("h3 a")
        title = (title_tag.get("title") or title_tag.get_text(strip=True)) if title_tag else ""
        href = title_tag.get("href") if title_tag else None
        price_tag = card.select_one("p.price_color")
        rating_tag = card.select_one("p.star-rating")
        rating_word = rating_tag.get("class", [""])[1] if rating_tag and len(rating_tag.get("class", [])) > 1 else ""
        if not title:
            continue
        records.append({
            "name": title,
            "price": _parse_price(price_tag.get_text(strip=True) if price_tag else ""),
            "currency": "GBP",
            "rating": _STAR_WORDS.get(rating_word, 0.0),
            "image": urljoin(result.url, card.select_one("img.thumbnail")["src"]) if card.select_one("img.thumbnail") else "",
            "seller": "Books To Scrape",
            "url": urljoin(result.url, href) if href else result.url,
            "_retrieved_at": result.retrieved_at.isoformat(),
            "_source_name": result.source_name,
        })
    return records


def _parse_price(text: str) -> float:
    match = re.search(r"[\d.]+", text)
    return float(match.group(0)) if match else 0.0


# -- Arbeitnow (job entity, JSON API) ------------------------------------------


def _extract_arbeitnow(payload: dict, result: fetcher.FetchResult) -> list[dict]:
    records = []
    for item in payload.get("data", []):
        title = str(item.get("title", "")).strip()
        if not title:
            continue
        job_types = item.get("job_types") or []
        records.append({
            "title": title,
            "company": str(item.get("company_name", "")).strip(),
            "salary": "",  # API does not expose salary; left empty rather than invented
            "currency": "EUR",
            "experience": ", ".join(str(t) for t in job_types),
            "location": str(item.get("location", "")).strip(),
            "url": str(item.get("url", "")).strip(),
            "_retrieved_at": result.retrieved_at.isoformat(),
            "_source_name": result.source_name,
        })
    return records


# -- Hacker News (record entity, JSON API) -------------------------------------


def extract_hn_hits(hits: list[dict], retrieved_at: datetime | None = None) -> list[dict]:
    """Shape HN Algolia story hits into the generic record schema."""
    when = (retrieved_at or datetime.now(timezone.utc)).isoformat()
    records = []
    for hit in hits:
        title = str(hit.get("title") or hit.get("story_title") or "").strip()
        if not title:
            continue
        url = str(hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}").strip()
        story_text = str(hit.get("story_text") or hit.get("comment_text") or "").strip()
        records.append({
            "title": title,
            "description": BeautifulSoup(story_text, "html.parser").get_text(" ", strip=True)[:500],
            "url": url,
            "_retrieved_at": when,
            "_source_name": "Hacker News Search (Algolia API)",
        })
    return records


# -- HN hits for the extract phase ---------------------------------------------


def extract_records(entity: str, query: str, offset: int, take: int) -> tuple[list[dict], dict]:
    """Extract up to `take` records for an entity, starting at global `offset`.

    Returns (records, search_meta). Slices by global record offset and keeps
    fetching deeper pages within the round until `take` is met or the source
    runs out, so one round can span several page fetches (rate limits apply).
    """
    if entity == "product":
        collected: list[dict] = []
        first_result = None
        page = (offset // _BOOKS_PAGE_SIZE) + 1
        start_in_page = offset % _BOOKS_PAGE_SIZE
        for pages_fetched in range(4):  # bounded: max 4 pages per round
            result = fetcher.fetch_url(BOOKS_CATALOGUE.format(page=page + pages_fetched))
            if first_result is None:
                first_result = result
            if not result.ok:
                break  # past the last catalogue page (404) or transient failure
            page_records = _extract_books(BeautifulSoup(result.content, "html.parser"), result)
            if not page_records:
                break
            slice_from = start_in_page if pages_fetched == 0 else 0
            collected.extend(page_records[slice_from:])
            start_in_page = 0
            if len(collected) >= take:
                break
        return collected[:take], _meta(first_result or fetcher._refused(url="", retrieved_at=_now(), error="no fetch"))

    if entity == "job":
        page = (offset // ARBEITNOW_PAGE_SIZE) + 1
        url = ARBEITNOW_API + (f"?page={page}" if page > 1 else "")
        result = fetcher.fetch_url(url)
        if not result.ok:
            return [], _meta(result)
        import json

        try:
            payload = json.loads(result.content)
        except ValueError:
            return [], _meta(result)
        records = _extract_arbeitnow(payload, result)
        start = offset % ARBEITNOW_PAGE_SIZE
        return records[start:start + take], _meta(result)

    # record entity: HN search response IS the payload; offset slices hits.
    hits = _hn_hits(query, page=offset // _HN_PAGE_SIZE)
    start = offset % _HN_PAGE_SIZE
    records = extract_hn_hits(hits[start:], retrieved_at=None)
    return records[:take], {"domain": "hn.algolia.com", "sourceName": source_policy.source_name("hn.algolia.com"), "sourceKind": "api", "retrievedAt": _now().isoformat(), "error": ""}


def _meta(result: fetcher.FetchResult) -> dict:
    return {
        "domain": result.domain,
        "sourceName": result.source_name,
        "sourceKind": result.source_kind,
        "retrievedAt": result.retrieved_at.isoformat(),
        "error": result.error,
    }
