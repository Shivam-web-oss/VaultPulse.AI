import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid4

from app.schemas.collection import (
    Dataset,
    DatasetData,
    DatasetProvenance,
    DatasetSchema,
    DatasetView,
    ProvenanceEntry,
    TaskStatus,
)


class CollectionTask:
    """In-memory collection task with filesystem artifact directories."""

    def __init__(self, task_id: str, prompt: str, runtime_root: Path) -> None:
        self.id = task_id
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

    def events_since(self, index: int) -> List[dict]:
        with self._lock:
            return list(self.events[index:])

    # -- state ---------------------------------------------------------------

    def set_status(self, status: TaskStatus) -> None:
        self.status = status
        self.updated_at = datetime.now(timezone.utc)

    def is_terminal(self) -> bool:
        return self.status in (TaskStatus.COMPLETED, TaskStatus.PARTIAL, TaskStatus.FAILED, TaskStatus.CANCELLED)

    def apply_records(self, records: List[dict], entries: List[ProvenanceEntry], schema: DatasetSchema, view: DatasetView) -> None:
        with self._lock:
            self.schema = schema
            self.view = view
            self.items = records
            self.provenance_entries = entries
            self.updated_at = datetime.now(timezone.utc)

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
        self.dir.mkdir(parents=True, exist_ok=True)
        path = self.dir / "dataset.json"
        path.write_text(
            json.dumps(json.loads(self.dataset().model_dump_json(by_alias=True)), indent=2),
            encoding="utf-8",
        )


class CollectionService:
    """Task store: in-memory registry + filesystem artifacts."""

    def __init__(self, runtime_root: Optional[Path] = None) -> None:
        self._tasks: Dict[str, CollectionTask] = {}
        self._lock = threading.Lock()
        self.runtime_root = Path(runtime_root) if runtime_root else Path("runtime") / "tasks"

    def create(self, prompt: str) -> CollectionTask:
        task = CollectionTask(str(uuid4()), prompt, self.runtime_root)
        task.dir.mkdir(parents=True, exist_ok=True)
        with self._lock:
            self._tasks[task.id] = task
        task.log_event("STATUS", {"taskId": task.id, "status": task.status.value})
        task.write_dataset()
        return task

    def get(self, task_id: str) -> Optional[CollectionTask]:
        return self._tasks.get(task_id)

    def cancel(self, task_id: str) -> bool:
        task = self._tasks.get(task_id)
        if task is None or task.is_terminal():
            return False
        task.cancel_requested = True
        task.set_status(TaskStatus.CANCELLED)
        task.log_event("STATUS", {"taskId": task.id, "status": TaskStatus.CANCELLED.value})
        return True

    def dataset_path(self, task_id: str) -> Path:
        return self.runtime_root / task_id / "dataset.json"

    def ui_path(self, task_id: str) -> Path:
        return self.runtime_root / task_id / "ui.html"


collection_service = CollectionService()
