"""LangGraph collection graph (doc §12 workflow, §11 state).

START → requirement_analyzer → workflow_planner → tool_selector
      → source_selection → search → open_pages → extract
      → normalize → validate → deduplicate
      → (enough valid records? NO → search more / YES →)
      → build_schema → build_dataset → END

UI generation is Phase F and is intentionally not a node yet.
"""

import time
from typing import List

from langgraph.graph import END, START, StateGraph

from app.ai import fake_collector
from app.ai.planner import plan
from app.ai.requirement_analyzer import Requirement, analyze
from app.ai.state import CollectionState
from app.processing import quality
from app.schemas.collection import ProvenanceEntry
from app.tools import registry

MAX_ROUNDS = 6


def _requirement(state: CollectionState) -> Requirement:
    return Requirement(
        entity=state["requirement"]["entity"],
        entity_label=state["requirement"]["entityLabel"],
        count=state["requirement"]["count"],
        constraints=state["requirement"]["constraints"],
        schema=state["requirement"].get("_schema"),
    )


# -- nodes -------------------------------------------------------------------


def requirement_analyzer(state: CollectionState) -> dict:
    requirement = analyze(state["prompt"])
    return {
        "requirement": {
            "entity": requirement.entity,
            "entityLabel": requirement.entity_label,
            "count": requirement.count,
            "constraints": requirement.constraints,
            "_schema": requirement.schema,
        },
        "target_count": requirement.count,
        "round": 0,
        "errors": [],
    }


def workflow_planner(state: CollectionState) -> dict:
    requirement = _requirement(state)
    workflow = plan(requirement)
    return {"workflow": workflow}


def tool_selector(state: CollectionState) -> dict:
    workflow = state["workflow"]
    return {"tool_calls": workflow["toolCalls"]}


def source_selection(state: CollectionState) -> dict:
    sources = []
    for call in state["tool_calls"]:
        if call["source"] not in sources:
            sources.append(call["source"])
    return {"sources": sources}


def search(state: CollectionState) -> dict:
    _requirement(state)  # validates state shape
    round_index = state["round"]
    rounds = state["workflow"]["rounds"]
    round_plan = rounds[round_index % len(rounds)]
    tool = registry.REGISTRY[round_plan["tool"]]
    result = tool.run(state["prompt"], _requirement(state), round_plan["source"], round_plan.get("offset", 0))
    return {
        "raw_evidence": [{
            "round": round_index + 1,
            "tool": round_plan["tool"],
            "source": round_plan["source"],
            "capacity": result.get("capacity"),
            "permitted": result.get("permitted", True),
        }],
        "round": round_index + 1,
    }


def open_pages(state: CollectionState) -> dict:
    pages = max(1, state["target_count"] // 20)
    return {"errors": state["errors"]}  # placeholder until Phase D browser tool


def extract(state: CollectionState) -> dict:
    round_plan = state["workflow"]["rounds"][(state["round"] - 1) % len(state["workflow"]["rounds"])]
    # Deterministic paging: advance the slice by how much earlier rounds took.
    prior_rounds = state["workflow"]["rounds"][: state["round"] - 1]
    offset = sum(r["take"] for r in prior_rounds)
    sliced = list(fake_collector.collect(_requirement(state)))[offset: offset + round_plan["take"]]
    records: List[dict] = []
    entries: List[ProvenanceEntry] = []
    for index, (record, entry) in enumerate(sliced):
        entry.recordIndex = offset + index
        records.append(record)
        entries.append(entry)
    return {"extracted_records": records, "provenance_entries": entries}


def normalize(state: CollectionState) -> dict:
    return {"normalized_records": state.get("extracted_records", [])}  # Phase E adds real normalization


def validate(state: CollectionState) -> dict:
    valid = quality.validate_records(state.get("normalized_records", []), _requirement(state))
    return {"valid_records": valid}


def deduplicate(state: CollectionState) -> dict:
    merged = quality.deduplicate_records(state.get("valid_records", []), state.get("final_records", []))
    return {"final_records": merged, "current_count": len(merged)}


def build_schema(state: CollectionState) -> dict:
    requirement = _requirement(state)
    schema = requirement.schema.model_dump(by_alias=True) if requirement.schema else {"name": "record", "version": "1.0", "fields": []}
    return {"schema": schema, "view": {"suggestedType": requirement.entity}}


def build_dataset(state: CollectionState) -> dict:
    return {"status": "READY"}


# -- conditional edge ----------------------------------------------------------


def enough_valid_records(state: CollectionState) -> str:
    if state["current_count"] >= state["target_count"]:
        return "yes"
    if state["round"] >= MAX_ROUNDS or state["round"] >= len(state["workflow"]["rounds"]):
        # Sources exhausted: report PARTIAL, never fabricate (doc §13).
        return "exhausted"
    return "no"


# -- graph assembly --------------------------------------------------------------


def build_graph():
    graph = StateGraph(CollectionState)
    graph.add_node("requirement_analyzer", requirement_analyzer)
    graph.add_node("workflow_planner", workflow_planner)
    graph.add_node("tool_selector", tool_selector)
    graph.add_node("source_selection", source_selection)
    graph.add_node("search", search)
    graph.add_node("open_pages", open_pages)
    graph.add_node("extract", extract)
    graph.add_node("normalize", normalize)
    graph.add_node("validate", validate)
    graph.add_node("deduplicate", deduplicate)
    graph.add_node("build_schema", build_schema)
    graph.add_node("build_dataset", build_dataset)

    graph.add_edge(START, "requirement_analyzer")
    graph.add_edge("requirement_analyzer", "workflow_planner")
    graph.add_edge("workflow_planner", "tool_selector")
    graph.add_edge("tool_selector", "source_selection")
    graph.add_edge("source_selection", "search")
    graph.add_edge("search", "open_pages")
    graph.add_edge("open_pages", "extract")
    graph.add_edge("extract", "normalize")
    graph.add_edge("normalize", "validate")
    graph.add_edge("validate", "deduplicate")
    graph.add_conditional_edges(
        "deduplicate",
        enough_valid_records,
        {"no": "search", "exhausted": "build_schema", "yes": "build_schema"},
    )
    graph.add_edge("build_schema", "build_dataset")
    graph.add_edge("build_dataset", END)
    return graph.compile()


app_graph = build_graph()
