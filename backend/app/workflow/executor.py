"""Workflow executor: runs the LangGraph collection graph for a task.

Each graph pass emits SSE events to the task's event log. The graph itself
owns the pipeline (Phase C); UI generation arrives in Phase F.
"""

import threading
import time
from typing import List

from app.ai.graph import app_graph, enough_valid_records
from app.ai.requirement_analyzer import Requirement, analyze
from app.schemas.collection import DatasetView, ProvenanceEntry, TaskStatus
from app.services.collection_service import CollectionTask

_NODE_EVENTS = {
    "requirement_analyzer": "PLANNING",
    "workflow_planner": "PLAN",
    "tool_selector": "TOOL_SELECTED",
    "source_selection": "SOURCE_SELECTED",
    "search": "SEARCHING",
    "open_pages": "PAGE_OPENED",
    "extract": "RECORDS_FOUND",
    "normalize": "PROCESSING",
    "validate": "VALIDATING",
    "deduplicate": "DEDUPLICATING",
    "build_schema": "GENERATING_UI",
    "build_dataset": "DATASET_READY",
}

# State keys reduced with append semantics in CollectionState; streamed node
# updates for these must be extended, not replaced, or earlier rounds' data
# (notably provenance_entries) would be lost from the final snapshot.
_APPEND_KEYS = {"raw_evidence", "extracted_records", "provenance_entries"}


def _cancelled(task: CollectionTask) -> bool:
    return task.cancel_requested or task.status == TaskStatus.CANCELLED


def _run(task: CollectionTask) -> None:
    task.log_event("PLANNING", {"taskId": task.id})
    final_state = {}
    for chunk in app_graph.stream({"prompt": task.prompt}, stream_mode="updates"):
        for node, update in chunk.items():
            if _cancelled(task):
                return
            for key, value in (update or {}).items():
                if key in _APPEND_KEYS and isinstance(value, list):
                    final_state.setdefault(key, []).extend(value)
                else:
                    final_state[key] = value
            payload = dict(update or {})
            event = _NODE_EVENTS.get(node, node.upper())
            task.log_event(event, _compact(payload))
            time.sleep(0.05)  # make progress observable over SSE and cancellable
            if node == "extract":
                extracted = len(payload.get("extracted_records", []))
                if extracted:
                    task.log_event("RECORDS_FOUND", {"found": extracted, "target": payload.get("target_count")})
            if node == "deduplicate":
                task.log_event("PROGRESS", {"current": payload.get("current_count", 0)})

    # Publish final records into the task and persist the dataset.
    # Cap over-delivery at the requested count (rounds over-fetch to absorb
    # validation attrition; the dataset should match what the user asked for).
    records: List[dict] = final_state.get("final_records", [])
    target = final_state.get("target_count")
    if target and len(records) > target:
        records = records[:target]
    entries = _match_provenance(final_state.get("provenance_entries", []), records)
    schema = final_state.get("schema") or {"name": "record", "version": "1.0", "fields": []}
    view = DatasetView(**(final_state.get("view") or {}))
    task.apply_records(records, entries, _schema_from(schema), view)
    status = TaskStatus.COMPLETED if len(records) >= final_state.get("target_count", len(records)) else TaskStatus.PARTIAL
    task.set_status(status)
    task.write_dataset()
    task.log_event(
        "COMPLETED" if status == TaskStatus.COMPLETED else "PARTIAL",
        {"records": len(records), "requested": final_state.get("target_count")},
    )


def _compact(payload: dict) -> dict:
    """Deep-clean a node update into JSON-safe SSE payload (drops _private keys)."""
    clean = {}
    for key, value in payload.items():
        if key.startswith("_"):
            continue
        clean[key] = _json_safe(value)
    return clean


def _json_safe(value):
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items() if not str(k).startswith("_")}
    if isinstance(value, (list, tuple)):
        if value and all(isinstance(item, ProvenanceEntry) for item in value):
            return len(value)  # record counts only; full entries are persisted in the task JSONB dataset
        return [_json_safe(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if hasattr(value, "model_dump"):
        return {k: v for k, v in value.model_dump(by_alias=True).items() if not str(k).startswith("_")}
    return str(value)


def _match_provenance(entries: List[ProvenanceEntry], records: List[dict]) -> List[ProvenanceEntry]:
    by_url = {entry.sourceUrl: entry for entry in entries if entry.sourceUrl}
    matched = []
    for index, record in enumerate(records):
        entry = (
            by_url.get(str(record.get("url", "")))
            or by_url.get(str(record.get("_source_url", "")))
            or by_url.get(str(record.get("_raw", {}).get("url", "")))
        )
        if entry is not None:
            entry.recordIndex = index
            matched.append(entry)
    return matched


def _schema_from(schema: dict):
    from app.schemas.collection import DatasetSchema

    return DatasetSchema(**schema)


def start(task: CollectionTask) -> None:
    def runner():
        try:
            task.set_status(TaskStatus.RUNNING)
            _run(task)
        except Exception as error:  # noqa: BLE001 - task must always reach a terminal state
            task.set_status(TaskStatus.FAILED)
            task.log_event("FAILED", {"error": str(error)})
            task.write_dataset()

    thread = threading.Thread(target=runner, name=f"collection-{task.id[:8]}", daemon=True)
    thread.start()
