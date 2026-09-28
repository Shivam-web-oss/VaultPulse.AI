import json
import logging
import threading
from datetime import datetime, timezone
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
    """Collection task backed by the collection_tasks JSONB dataset."""

    def __init__(self, task_id: str, prompt: str, owner_id: str, parent_task_id: Optional[str] = None, version: int = 1) -> None:
        self.id = task_id
        self.owner_id = owner_id
        self.parent_task_id = parent_task_id
        self.version = version
        self.prompt = prompt
        self.status = TaskStatus.CREATED
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = self.created_at
        self.view = DatasetView()
        self.schema = DatasetSchema(name="record", version="1.0", fields=[])
        self.items: List[dict] = []
        self.provenance_entries: List[ProvenanceEntry] = []
        self.events: List[dict] = []
        self.cancel_requested = False
        self._lock = threading.Lock()

    @classmethod
    def from_row(cls, row: dict) -> "CollectionTask":
        task = cls(str(row["id"]), row["prompt"], str(row["owner_id"]))
        task.status = TaskStatus(row["status"])
        task.created_at = row["created_at"]
        task.updated_at = row["updated_at"]
        task.parent_task_id = str(row["parent_task_id"]) if row.get("parent_task_id") else None
        task.version = row.get("version", 1)
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



class CollectionService:
    """Task store: in-memory task cache backed by Supabase Postgres."""

    def __init__(self) -> None:
        self._tasks: Dict[str, CollectionTask] = {}
        self._lock = threading.Lock()

    def create(self, prompt: str, owner_id: str) -> CollectionTask:
        task = CollectionTask(str(uuid4()), prompt, owner_id)
        with self._lock:
            self._tasks[task.id] = task
        with connection() as conn:
            conn.execute("insert into collection_tasks (id, owner_id, prompt, status) values (%s, %s, %s, %s)", (task.id, owner_id, prompt, task.status.value))
            conn.commit()
        task.log_event("STATUS", {"taskId": task.id, "status": task.status.value})
        task.write_dataset()
        logger.info("collection.created task_id=%s", task.id)
        return task

    def rerun(self, task_id: str, owner_id: str, prompt: Optional[str] = None) -> Optional[CollectionTask]:
        """Append one queued child to the task's root chain under a root-row lock."""
        with connection() as conn:
            with conn.transaction():
                ancestors = conn.execute(
                    """with recursive ancestry(id, parent_task_id, path) as (
                           select id, parent_task_id, array[id] from collection_tasks
                           where id = %s and owner_id = %s
                           union all
                           select p.id, p.parent_task_id, a.path || p.id
                           from collection_tasks p join ancestry a on p.id = a.parent_task_id
                           where p.owner_id = %s and not p.id = any(a.path)
                       ) select id from ancestry where parent_task_id is null limit 1""",
                    (task_id, owner_id, owner_id),
                ).fetchone()
                if ancestors is None:
                    return None

                root_id = ancestors["id"]
                conn.execute("select id from collection_tasks where id = %s for update", (root_id,)).fetchone()
                requested = conn.execute(
                    "select prompt from collection_tasks where id = %s and owner_id = %s",
                    (task_id, owner_id),
                ).fetchone()
                if requested is None:
                    return None
                leaf = conn.execute(
                    """with recursive descendants(id, parent_task_id, version, created_at, depth) as (
                           select id, parent_task_id, version, created_at, 0 from collection_tasks
                           where id = %s and owner_id = %s
                           union all
                           select c.id, c.parent_task_id, c.version, c.created_at, d.depth + 1
                           from collection_tasks c join descendants d on c.parent_task_id = d.id
                           where c.owner_id = %s
                       ) select d.id, d.version, t.prompt from descendants d
                         join collection_tasks t using (id)
                         where not exists (select 1 from collection_tasks c where c.parent_task_id = d.id and c.owner_id = %s)
                         order by depth desc, created_at desc limit 1""",
                    (root_id, owner_id, owner_id, owner_id),
                ).fetchone()
                if leaf is None:
                    return None
                new_id = str(uuid4())
                next_version = int(leaf["version"]) + 1
                new_prompt = prompt if prompt is not None else requested["prompt"]
                row = conn.execute(
                    """insert into collection_tasks
                       (id, owner_id, prompt, status, parent_task_id, version)
                       values (%s, %s, %s, %s, %s, %s)
                       returning created_at, updated_at""",
                    (new_id, owner_id, new_prompt, TaskStatus.QUEUED.value, leaf["id"], next_version),
                ).fetchone()

        task = CollectionTask(new_id, new_prompt, owner_id, str(leaf["id"]), next_version)
        task.status = TaskStatus.QUEUED
        task.created_at = row["created_at"]
        task.updated_at = row["updated_at"]
        task.write_dataset()
        with self._lock:
            self._tasks[task.id] = task
        task.log_event("STATUS", {"taskId": task.id, "status": task.status.value})
        logger.info("collection.rerun_created task_id=%s parent_task_id=%s version=%s", task.id, task.parent_task_id, task.version)
        return task

    def get(self, task_id: str, owner_id: str) -> Optional[CollectionTask]:
        with connection() as conn:
            row = conn.execute("select id, owner_id, prompt, status, created_at, updated_at, dataset, cancel_requested, parent_task_id, version from collection_tasks where id = %s and owner_id = %s", (task_id, owner_id)).fetchone()
        if row is None:
            return None
        task = self._tasks.get(task_id)
        if task is not None:
            return task
        return CollectionTask.from_row(row)

    def history(self, task_id: str, owner_id: str) -> Optional[List[CollectionTask]]:
        with connection() as conn:
            start = conn.execute(
                "select id, parent_task_id from collection_tasks where id = %s and owner_id = %s",
                (task_id, owner_id),
            ).fetchone()
            if start is None:
                return None
            cursor = start
            seen = set()
            while cursor["parent_task_id"] is not None:
                parent_id = str(cursor["parent_task_id"])
                if parent_id in seen:
                    raise ValueError("Cycle found in collection task history")
                seen.add(parent_id)
                parent = conn.execute(
                    "select id, parent_task_id from collection_tasks where id = %s and owner_id = %s",
                    (parent_id, owner_id),
                ).fetchone()
                if parent is None:
                    break
                cursor = parent
            root_id = cursor["id"]
            rows = conn.execute(
                """with recursive chain(id, depth, path) as (
                       select id, 0, array[id] from collection_tasks where id = %s and owner_id = %s
                       union all
                       select c.id, chain.depth + 1, chain.path || c.id
                       from collection_tasks c join chain on c.parent_task_id = chain.id
                       where c.owner_id = %s and not c.id = any(chain.path)
                   )
                   select t.id, t.owner_id, t.prompt, t.status, t.created_at, t.updated_at,
                          t.dataset, t.cancel_requested, t.parent_task_id, t.version
                   from chain join collection_tasks t using (id) order by chain.depth, t.created_at""",
                (root_id, owner_id, owner_id),
            ).fetchall()
        return [CollectionTask.from_row(row) for row in rows]

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

collection_service = CollectionService()
