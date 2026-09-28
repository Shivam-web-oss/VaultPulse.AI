import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid4

from app.db import connection
from psycopg.types.json import Jsonb
from app.schemas.collection import (
    Dataset,
    DatasetData,
    DatasetProvenance,
    DatasetSchema,
    DatasetView,
    ProvenanceEntry,
    TaskStatus,
)

logger = logging.getLogger(__name__)


class CollectionTask:
    """In-memory collection task with filesystem artifact directories."""

    def __init__(self, task_id: str, prompt: str, runtime_root: Path, owner_id: str) -> None:
        self.id = task_id
        self.owner_id = owner_id
        self.prompt = prompt
        self.status = TaskStatus.CREATED
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = self.created_at
        self.dir = runtime_root / task_id
        self.view = DatasetView()
        self.schema = DatasetSchema(name="record", version="1.0", fields=[])
        self.items: List[dict] = []
        self.provenance_entries: List[ProvenanceEntry] = []
        self.events: List[dict] = []
        self.cancel_requested = False
        self._lock = threading.Lock()

    @classmethod
    def from_row(cls, row: dict, runtime_root: Path) -> "CollectionTask":
        task = cls(str(row["id"]), row["prompt"], runtime_root, str(row["owner_id"]))
        task.status = TaskStatus(row["status"])
        task.created_at = row["created_at"]
        task.updated_at = row["updated_at"]
        task.cancel_requested = row["cancel_requested"]
        payload = row.get("dataset") or {}
        if payload:
            dataset = Dataset.model_validate(payload)
            task.view = dataset.view
            task.schema = dataset.schema_
            task.items = dataset.data.items
            task.provenance_entries = dataset.provenance.entries
        return task

    @property
    def count(self) -> int:
        return len(self.items)

    # -- events ------------------------------------------------------------

    def log_event(self, event_type: str, payload: Optional[dict] = None) -> None:
        event = {
            "event": event_type,
            "data": payload or {},
            "at": datetime.now(timezone.utc).isoformat(),
        }
        with self._lock:
            self.events.append(event)
        with connection() as conn:
            conn.execute("insert into collection_events (task_id, event, data) values (%s, %s, %s)", (self.id, event_type, Jsonb(event["data"])))
            conn.commit()
        logger.info("collection.event task_id=%s event=%s", self.id, event_type)

    def events_since(self, index: int) -> List[dict]:
        with connection() as conn:
            rows = conn.execute("select event, data, created_at from collection_events where task_id = %s order by id offset %s", (self.id, index)).fetchall()
        return [{"event": row["event"], "data": row["data"], "at": row["created_at"].isoformat()} for row in rows]

    # -- state ---------------------------------------------------------------

    def set_status(self, status: TaskStatus) -> None:
        self.status = status
        self.updated_at = datetime.now(timezone.utc)
        with connection() as conn:
            conn.execute("update collection_tasks set status = %s, updated_at = %s where id = %s", (status.value, self.updated_at, self.id))
            conn.commit()
        logger.info("collection.status_changed task_id=%s status=%s", self.id, status.value)

    def is_terminal(self) -> bool:
        return self.status in (TaskStatus.COMPLETED, TaskStatus.PARTIAL, TaskStatus.FAILED, TaskStatus.CANCELLED)

    def apply_records(self, records: List[dict], entries: List[ProvenanceEntry], schema: DatasetSchema, view: DatasetView) -> None:
        with self._lock:
            self.schema = schema
            self.view = view
            self.items = records
            self.provenance_entries = entries
            self.updated_at = datetime.now(timezone.utc)
            logger.info("collection.records_applied task_id=%s record_count=%s provenance_count=%s", self.id, len(records), len(entries))

    # -- dataset -------------------------------------------------------------

    def dataset(self) -> Dataset:
        return Dataset(
            request={"prompt": self.prompt},
            view=self.view,
            schema=self.schema,
            data=DatasetData(count=self.count, items=self.items),
            provenance=DatasetProvenance(retrievedAt=self.updated_at, entries=self.provenance_entries),
        )

    def write_dataset(self) -> None:
        dataset_dict = json.loads(self.dataset().model_dump_json(by_alias=True))
        with connection() as conn:
            conn.execute(
                "update collection_tasks set dataset = %s, updated_at = %s where id = %s",
                (Jsonb(dataset_dict), self.updated_at, self.id),
            )
            conn.commit()

        # Ephemeral local cache (graceful on read-only environments like Vercel)
        try:
            self.dir.mkdir(parents=True, exist_ok=True)
            path = self.dir / "dataset.json"
            path.write_text(json.dumps(dataset_dict, indent=2), encoding="utf-8")
        except OSError as error:
            logger.debug("Local filesystem write skipped (read-only environment): %s", error)


class CollectionService:
    """Task store: in-memory registry + filesystem artifacts."""

    def __init__(self, runtime_root: Optional[Path] = None) -> None:
        self._tasks: Dict[str, CollectionTask] = {}
        self._lock = threading.Lock()
        self.runtime_root = Path(runtime_root) if runtime_root else Path("runtime") / "tasks"

    def create(self, prompt: str, owner_id: str) -> CollectionTask:
        task = CollectionTask(str(uuid4()), prompt, self.runtime_root, owner_id)
        try:
            task.dir.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            logger.debug("Local directory creation skipped: %s", error)
        with self._lock:
            self._tasks[task.id] = task
        with connection() as conn:
            conn.execute("insert into collection_tasks (id, owner_id, prompt, status) values (%s, %s, %s, %s)", (task.id, owner_id, prompt, task.status.value))
            conn.commit()
        task.log_event("STATUS", {"taskId": task.id, "status": task.status.value})
        task.write_dataset()
        logger.info("collection.created task_id=%s", task.id)
        return task

    def get(self, task_id: str, owner_id: str) -> Optional[CollectionTask]:
        with connection() as conn:
            row = conn.execute("select id, owner_id, prompt, status, created_at, updated_at, dataset, cancel_requested from collection_tasks where id = %s and owner_id = %s", (task_id, owner_id)).fetchone()
        if row is None:
            return None
        task = self._tasks.get(task_id)
        if task is not None:
            return task
        return CollectionTask.from_row(row, self.runtime_root)

    def cancel(self, task_id: str, owner_id: str) -> bool:
        task = self.get(task_id, owner_id)
        if task is None or task.is_terminal():
            return False
        task.cancel_requested = True
        with connection() as conn:
            conn.execute("update collection_tasks set cancel_requested = true where id = %s and owner_id = %s", (task_id, owner_id))
            conn.commit()
        task.set_status(TaskStatus.CANCELLED)
        task.log_event("STATUS", {"taskId": task.id, "status": TaskStatus.CANCELLED.value})
        return True

    def dataset_path(self, task_id: str) -> Path:
        return self.runtime_root / task_id / "dataset.json"

    def ui_path(self, task_id: str) -> Path:
        return self.runtime_root / task_id / "ui.html"


collection_service = CollectionService()
