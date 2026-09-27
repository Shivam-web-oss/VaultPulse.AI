import json
import logging
import time

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, StreamingResponse

from app.dependencies.auth import get_current_user
from app.schemas.auth import AuthUser
from app.schemas.collection import (
    CancelResponse,
    CollectionCreateRequest,
    CollectionCreatedResponse,
    CollectionResultResponse,
    CollectionStatusResponse,
)
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
    )


@router.post("", response_model=CollectionCreatedResponse, status_code=201)
def create_collection(payload: CollectionCreateRequest, current_user: AuthUser = Depends(get_current_user)):
    task = collection_service.create(payload.prompt, current_user.id)
    # Report the creation status, not whatever the executor has already moved to.
    response = CollectionCreatedResponse(taskId=task.id, status=task.status)
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
    ui_path = collection_service.ui_path(task_id)
    return CollectionResultResponse(
        request={"prompt": task.prompt, "status": task.status.value},
        dataset=dataset_payload,
        ui={"type": "generated_html", "artifact": "ui.html", "available": ui_path.exists()},
        provenance=dataset_payload.get("provenance", {}).get("entries", []),
        files={"dataset": "dataset.json", "ui": "ui.html"},
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
    if format != "json":
        raise HTTPException(status_code=400, detail="Unsupported export format")

    dataset_path = collection_service.dataset_path(task_id)
    if not dataset_path.exists():
        raise HTTPException(status_code=404, detail="Dataset artifact not found")
    return FileResponse(dataset_path, media_type="application/json", filename=f"dataset-{task_id}.json")


@router.get("/{task_id}/ui")
def get_ui(task_id: str, current_user: AuthUser = Depends(get_current_user)):
    task = collection_service.get(task_id, current_user.id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    ui_path = collection_service.ui_path(task_id)
    if not ui_path.exists():
        raise HTTPException(status_code=404, detail="UI artifact not generated yet")
    return FileResponse(ui_path, media_type="text/html", filename="ui.html")


@router.post("/{task_id}/cancel", response_model=CancelResponse)
def cancel_collection(task_id: str, current_user: AuthUser = Depends(get_current_user)):
    cancelled = collection_service.cancel(task_id, current_user.id)
    task = collection_service.get(task_id, current_user.id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return CancelResponse(taskId=task_id, status=task.status, cancelled=cancelled)
