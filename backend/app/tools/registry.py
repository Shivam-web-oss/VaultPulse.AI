"""Tool registry (doc §15).

AI decides WHAT should happen; application code decides HOW it can happen.
Only registered tools are selectable, and only permitted sources are accessed.

Phase D: tools call real permitted sources (scraping sandbox, keyless APIs)
through app.tools.sources and app.tools.fetcher, which enforce the
allow-list, robots.txt, and per-domain rate limits. The Tool contract —
run(query, requirement, source, offset) -> dict — is unchanged from Phase C.
"""

from dataclasses import dataclass
from typing import Callable, Dict, List

from app.ai.requirement_analyzer import Requirement
from app.tools import source_policy, sources

# Real permitted sources: domain -> (entity, planning capacity).
# Capacity is the practical per-run yield used by the workflow planner.
_SOURCE_POOL = {
    "books.toscrape.com": ("product", 600),        # 10 catalogue pages x ~20 records
    "www.arbeitnow.com": ("job", 325),             # one API page
    "hn.algolia.com": ("record", 200),             # paged search hits
}

_TOOL_BY_ENTITY = {
    "product": "books.toscrape.com",
    "job": "www.arbeitnow.com",
    "record": "hn.algolia.com",
}


@dataclass
class Tool:
    name: str
    description: str
    permitted_sources: tuple
    run: Callable


def _search_run(query: str, requirement: Requirement, source: str, offset: int) -> dict:
    """Discover real candidate URLs from a permitted source."""
    if not source_policy.is_permitted(source):
        return {"results": [], "source": source, "permitted": False}
    entity, capacity = _SOURCE_POOL[source]
    try:
        candidates = sources.find_candidates(entity, query, offset, take=requirement.count)
    except Exception as error:  # noqa: BLE001 - tool must not crash the graph
        return {"results": [], "source": source, "permitted": True, "error": str(error)}
    return {
        "results": [
            {"url": c.url, "label": c.label, "offset": c.offset_hint}
            for c in candidates
        ],
        "source": source,
        "entity": entity,
        "capacity": capacity,
        "offset": offset,
        "query": query,
        "permitted": True,
    }


def _extract_run(query: str, requirement: Requirement, source: str, offset: int) -> dict:
    """Extract records from a permitted source via real fetch + selectors/JSON walk."""
    if not source_policy.is_permitted(source):
        return {"items": [], "source": source, "permitted": False}
    entity, _capacity = _SOURCE_POOL[source]
    try:
        records, meta = sources.extract_records(entity, query, offset, take=requirement.count)
    except Exception as error:  # noqa: BLE001 - tool must not crash the graph
        return {"items": [], "source": source, "permitted": True, "error": str(error)}
    domain = meta.get("domain") or source
    for record in records:
        record["_source_url"] = str(record.get("url", ""))
        record["_source_name"] = record.get("_source_name") or source_policy.source_name(domain)
        record["_retrieved_at"] = record.get("_retrieved_at") or meta.get("retrievedAt")
    return {
        "items": [{"record": r, "provenance": {
            "sourceUrl": r.get("_source_url", ""),
            "sourceName": r.get("_source_name", ""),
            "retrievedAt": r.get("_retrieved_at", ""),
        }} for r in records],
        "source": source,
        "permitted": True,
    }


def _fetch_run(query: str, requirement: Requirement, source: str, offset: int) -> dict:
    """Fetch a page (or the first page of an API) for evidence under full policy."""
    if not source_policy.is_permitted(source):
        return {"status": "refused", "source": source, "error": "domain not permitted"}
    from app.tools.fetcher import fetch_url

    url = source if "://" in source else f"https://{source}"
    entity, _capacity = _SOURCE_POOL[source]
    candidates = sources.find_candidates(entity, query, offset, take=1)
    if candidates:
        url = candidates[0].url
    result = fetch_url(url)
    return {
        "status": "ok" if result.ok else "failed",
        "source": source,
        "url": result.url,
        "httpStatus": result.status,
        "bytes": len(result.content),
        "retrievedAt": result.retrieved_at.isoformat(),
        "error": result.error,
    }


SEARCH_TOOL = Tool(
    name="WebSearchTool",
    description="Searches a permitted source for real candidate URLs.",
    permitted_sources=tuple(_SOURCE_POOL),
    run=_search_run,
)
EXTRACT_TOOL = Tool(
    name="PageExtractionTool",
    description="Extracts structured records from a permitted source.",
    permitted_sources=tuple(_SOURCE_POOL),
    run=_extract_run,
)
FETCH_TOOL = Tool(
    name="HttpFetchTool",
    description="Fetches a permitted page for evidence.",
    permitted_sources=tuple(_SOURCE_POOL),
    run=_fetch_run,
)

REGISTRY: Dict[str, Tool] = {tool.name: tool for tool in (SEARCH_TOOL, EXTRACT_TOOL, FETCH_TOOL)}


def select_tools(entity: str) -> List[dict]:
    """Planner-facing tool selection: which registered tools apply to this entity."""
    return [
        {"name": SEARCH_TOOL.name, "source": _pick_source(entity, SEARCH_TOOL.permitted_sources)},
        {"name": EXTRACT_TOOL.name, "source": _pick_source(entity, EXTRACT_TOOL.permitted_sources)},
    ]


def _pick_source(entity: str, permitted: tuple) -> str:
    return _TOOL_BY_ENTITY.get(entity, permitted[0] if permitted else "hn.algolia.com")


def source_capacity(source: str) -> int:
    return _SOURCE_POOL.get(source, ("record", 0))[1]
