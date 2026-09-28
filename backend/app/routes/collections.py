import json
import logging
import time
from typing import Any, List, Optional
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import FileResponse, StreamingResponse

from app.dependencies.auth import get_current_user
from app.processing.quality import validate_records
from app.schemas.auth import AuthUser
from app.schemas.collection import (
    CancelResponse,
    CollectionCreateRequest,
    CollectionCreatedResponse,
    CollectionDataResponse,
    CollectionHistoryEntry,
    CollectionRerunRequest,
    CollectionResultResponse,
    CollectionStatusResponse,
)
from app.services.collection_query import query_collection_items, stream_csv
from app.services.collection_service import collection_service
from app.workflow import executor

router = APIRouter(prefix="/v1/collections", tags=["collections"])
logger = logging.getLogger(__name__)


def _status_response(task) -> CollectionStatusResponse:
    return CollectionStatusResponse(
        taskId=task.id,
        status=task.status,
        prompt=task.prompt,
        createdAt=task.created_at,
        updatedAt=task.updated_at,
        recordCount=task.count,
        parentTaskId=task.parent_task_id,
        version=task.version,
    )


@router.post("", response_model=CollectionCreatedResponse, status_code=201)
def create_collection(payload: CollectionCreateRequest, current_user: AuthUser = Depends(get_current_user)):
    task = collection_service.create(payload.prompt, current_user.id)
    # Report the creation status, not whatever the executor has already moved to.
    response = CollectionCreatedResponse(
        taskId=task.id, status=task.status, parentTaskId=task.parent_task_id, version=task.version,
    )
    executor.start(task)
    logger.info("collection.request_started task_id=%s user_id=%s", task.id, current_user.id)
    return response


@router.get("/{task_id}", response_model=CollectionStatusResponse)
def get_collection(task_id: str, current_user: AuthUser = Depends(get_current_user)):
    task = collection_service.get(task_id, current_user.id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return _status_response(task)


@router.get("/{task_id}/result", response_model=CollectionResultResponse)
def get_result(task_id: str, current_user: AuthUser = Depends(get_current_user)):
    task = collection_service.get(task_id, current_user.id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    dataset_payload = json.loads(task.dataset().model_dump_json(by_alias=True))
    provenance_entries = dataset_payload.get("provenance", {}).get("entries", [])

    # Extract unique source names and URLs
    sources: List[str] = []
    seen_sources = set()
    for entry in provenance_entries:
        src = entry.get("sourceName") or entry.get("sourceUrl")
        if src and src not in seen_sources:
            seen_sources.add(src)
            sources.append(src)

    # Calculate validation quality stats across records
    val_result = validate_records(task.items, task.schema)
    summary = val_result.summary

    return CollectionResultResponse(
        request={"prompt": task.prompt, "status": task.status.value},
        dataset=dataset_payload,
        ui={"type": "api_only", "available": False, "description": "Interactive dashboard driven by API"},
        provenance=provenance_entries,
        files={},
        summary=summary,
        quality=summary,
        sources=sources,
        parentTaskId=task.parent_task_id,
        version=task.version,
    )


@router.post("/{task_id}/rerun", response_model=CollectionCreatedResponse, status_code=201)
def rerun_collection(
    task_id: str,
    payload: Optional[CollectionRerunRequest] = None,
    current_user: AuthUser = Depends(get_current_user),
):
    task = collection_service.rerun(task_id, current_user.id, payload.prompt if payload else None)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    response = CollectionCreatedResponse(
        taskId=task.id, status=task.status, parentTaskId=task.parent_task_id, version=task.version,
    )
    executor.start(task)
    logger.info("collection.rerun_started task_id=%s parent_task_id=%s user_id=%s", task.id, task.parent_task_id, current_user.id)
    return response


@router.get("/{task_id}/history", response_model=List[CollectionHistoryEntry])
def get_collection_history(task_id: str, current_user: AuthUser = Depends(get_current_user)):
    try:
        tasks = collection_service.history(task_id, current_user.id)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    if tasks is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return [
        CollectionHistoryEntry(
            taskId=task.id,
            version=task.version,
            status=task.status,
            createdAt=task.created_at,
            prompt=task.prompt,
            recordCount=task.count,
            quality=validate_records(task.items, task.schema).summary if task.items else None,
        )
        for task in tasks
    ]


def _diff_key_field(task) -> Optional[str]:
    available = {field.key for field in task.schema.fields}
    return next((field for field in ("url", "website", "source_url", "domain", "name") if field in available), None)


def _normalize_diff_key(value: Any, field: str) -> str:
    text = str(value or "").strip().casefold()
    if field in {"url", "website", "source_url"}:
        parsed = urlsplit(text if "://" in text else f"//{text}")
        host = (parsed.netloc or parsed.path).removeprefix("www.")
        path = parsed.path.rstrip("/") if parsed.netloc else ""
        return f"{host}{path}".rstrip("/")
    return " ".join(text.split())


@router.get("/{task_id}/diff/{other_id}")
def diff_collections(task_id: str, other_id: str, current_user: AuthUser = Depends(get_current_user)):
    before = collection_service.get(task_id, current_user.id)
    after = collection_service.get(other_id, current_user.id)
    if before is None or after is None:
        raise HTTPException(status_code=404, detail="Task not found")
    key_field = _diff_key_field(before)
    if key_field is None or key_field not in {field.key for field in after.schema.fields}:
        raise HTTPException(status_code=400, detail="Cannot diff datasets: both schemas need a shared url, website, source_url, domain, or name field")

    def keyed(items):
        result = {}
        for item in items:
            key = _normalize_diff_key(item.get(key_field), key_field)
            if not key:
                raise HTTPException(status_code=400, detail=f"Cannot diff dataset: item is missing stable key '{key_field}'")
            if key in result:
                raise HTTPException(status_code=400, detail=f"Cannot diff dataset: stable key '{key_field}' is not unique")
            result[key] = item
        return result

    old_items, new_items = keyed(before.items), keyed(after.items)
    added_keys = new_items.keys() - old_items.keys()
    removed_keys = old_items.keys() - new_items.keys()
    changed = []
    for key in old_items.keys() & new_items.keys():
        old, new = old_items[key], new_items[key]
        fields = sorted(field for field in old.keys() | new.keys() if old.get(field) != new.get(field))
        if fields:
            changed.append({"key": key, "fields": fields, "before": old, "after": new})
    return {
        "keyField": key_field,
        "added": [new_items[key] for key in sorted(added_keys)],
        "removed": [old_items[key] for key in sorted(removed_keys)],
        "changed": sorted(changed, key=lambda entry: entry["key"]),
    }


@router.get("/{task_id}/data")
def get_collection_data(
    task_id: str,
    search: Optional[str] = None,
    filter: Optional[List[str]] = Query(None),
    sort: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    format: Optional[str] = Query(None),
    current_user: AuthUser = Depends(get_current_user),
) -> Any:
    """Query, filter, search, sort, and paginate collection records.

    Supports JSON pagination and CSV streaming with identical query filters.
    """
    task = collection_service.get(task_id, current_user.id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    if format and format not in ("json", "csv"):
        raise HTTPException(status_code=400, detail="Unsupported format: must be 'json' or 'csv'")

    items, total = query_collection_items(
        raw_items=task.items,
        schema=task.schema,
        search=search,
        filter_param=filter,
        sort_param=sort,
        page=page,
        page_size=page_size,
        default_fetched_at=task.updated_at.isoformat(),
    )

    if format == "csv":
        return StreamingResponse(
            stream_csv(items, task.schema),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="collection-{task_id}.csv"'},
        )

    return CollectionDataResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=items,
    )


@router.get("/{task_id}/events")
def stream_events(task_id: str, current_user: AuthUser = Depends(get_current_user)):
    task = collection_service.get(task_id, current_user.id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    def event_stream():
        index = 0
        while True:
            events = task.events_since(index)
            for event in events:
                index += 1
                yield f"event: {event['event']}\ndata: {json.dumps(event['data'])}\n\n"
            if task.is_terminal():
                break
            time.sleep(0.2)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/{task_id}/export")
def export_dataset(task_id: str, format: str = "json", current_user: AuthUser = Depends(get_current_user)):
    task = collection_service.get(task_id, current_user.id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if format not in ("json", "csv"):
        raise HTTPException(status_code=400, detail="Unsupported export format: must be 'json' or 'csv'")

    if format == "json":
        dataset_content = task.dataset().model_dump_json(by_alias=True, indent=2)
        return Response(
            content=dataset_content,
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="dataset-{task_id}.json"'},
        )
    else:
        return StreamingResponse(
            stream_csv(task.items, task.schema),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="dataset-{task_id}.csv"'},
        )


@router.post("/{task_id}/cancel", response_model=CancelResponse)
def cancel_collection(task_id: str, current_user: AuthUser = Depends(get_current_user)):
    cancelled = collection_service.cancel(task_id, current_user.id)
    task = collection_service.get(task_id, current_user.id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return CancelResponse(taskId=task_id, status=task.status, cancelled=cancelled)
