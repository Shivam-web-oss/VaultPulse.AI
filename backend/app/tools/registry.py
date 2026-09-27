"""Tool registry (doc §15).

AI decides WHAT should happen; application code decides HOW it can happen.
Only registered tools are selectable, and only permitted sources are accessed.
Phase C uses deterministic fake tools; Phase D swaps their implementations.
"""

from dataclasses import dataclass
from typing import Callable, Dict, List

from app.ai.requirement_analyzer import Requirement

# Deterministic fake source pool. Phase D replaces these generators with real
# search/browse implementations; the registry contract stays identical.
_SOURCE_POOL = {
    "example-product-directory": ("product", 30),
    "example-marketplace-feed": ("product", 25),
    "example-jobs-board": ("job", 35),
    "example-events-calendar": ("event", 30),
    "example-web-index": ("record", 40),
}


@dataclass
class Tool:
    name: str
    description: str
    permitted_sources: tuple
    run: Callable


def _search_run(query: str, requirement: Requirement, source: str, offset: int) -> dict:
    from app.tools.source_policy import is_permitted

    if not is_permitted(source):
        return {"results": [], "source": source, "permitted": False}
    entity, capacity = _SOURCE_POOL[source]
    return {"source": source, "entity": entity, "capacity": capacity, "offset": offset, "query": query, "permitted": True}


def _extract_run(query: str, requirement: Requirement, source: str, offset: int) -> dict:
    from app.ai.fake_collector import collect

    requirement = Requirement(
        entity=requirement.entity,
        entity_label=requirement.entity_label,
        count=requirement.count,
        constraints=requirement.constraints,
        schema=requirement.schema,
    )
    collected = []
    for record, provenance in collect(requirement):
        collected.append({"record": record, "provenance": provenance})
    # Simulate paging: each round takes the next slice of the pool.
    return {"items": collected[offset:], "source": source}


def _fetch_run(query: str, requirement: Requirement, source: str, offset: int) -> dict:
    return {"status": "ok", "source": source, "note": "Phase D will fetch real pages"}


SEARCH_TOOL = Tool(
    name="WebSearchTool",
    description="Searches a permitted source directory for candidate items.",
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
    for source, (source_entity, _capacity) in _SOURCE_POOL.items():
        if source_entity == entity:
            return source
    return permitted[0]


def source_capacity(source: str) -> int:
    return _SOURCE_POOL.get(source, ("record", 0))[1]
