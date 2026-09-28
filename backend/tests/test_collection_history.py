from contextlib import contextmanager, nullcontext
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.routes import collections as routes
from app.schemas.collection import DatasetSchema, SchemaField, TaskStatus
from app.services import collection_service as service_module


class Result:
    def __init__(self, one=None, many=None):
        self.one = one
        self.many = many or ([] if one is None else [one])

    def fetchone(self):
        return self.one

    def fetchall(self):
        return self.many


class FakeDatabase:
    def __init__(self):
        self.rows = {}
        self.events = []

    def seed(self, task_id, parent_id=None, version=1, prompt="collect companies", items=None):
        now = datetime.now(timezone.utc)
        self.rows[task_id] = {
            "id": task_id, "owner_id": "user-1", "prompt": prompt,
            "status": "COMPLETED", "created_at": now, "updated_at": now,
            "dataset": {}, "cancel_requested": False,
            "parent_task_id": parent_id, "version": version,
            "items": items or [],
        }

    def connection(self):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def transaction(self):
        return nullcontext()

    def commit(self):
        pass

    def execute(self, sql, params=()):
        sql = " ".join(sql.split())
        if "with recursive ancestry" in sql:
            current = self.rows.get(params[0])
            if not current or current["owner_id"] != params[1]:
                return Result()
            visited = set()
            while current["parent_task_id"] is not None:
                if current["id"] in visited:
                    return Result()
                visited.add(current["id"])
                current = self.rows.get(current["parent_task_id"])
                if current is None or current["owner_id"] != params[1]:
                    return Result()
            return Result({"id": current["id"]})
        if "for update" in sql:
            return Result({"id": params[0]} if params[0] in self.rows else None)
        if sql.startswith("select prompt from collection_tasks"):
            row = self.rows.get(params[0])
            return Result({"prompt": row["prompt"]} if row and row["owner_id"] == params[1] else None)
        if "with recursive descendants" in sql:
            root_id = params[0]
            descendants = [self.rows[root_id]]
            while True:
                children = [row for row in self.rows.values() if row["parent_task_id"] == descendants[-1]["id"]]
                if not children:
                    break
                descendants.append(children[-1])
            leaf = descendants[-1]
            return Result({"id": leaf["id"], "version": leaf["version"], "prompt": leaf["prompt"]})
        if sql.startswith("insert into collection_tasks"):
            task_id, owner, prompt, status, parent_id, version = params
            self.seed(task_id, parent_id, version, prompt)
            self.rows[task_id]["owner_id"] = owner
            self.rows[task_id]["status"] = status
            return Result({"created_at": self.rows[task_id]["created_at"], "updated_at": self.rows[task_id]["updated_at"]})
        if sql.startswith("update collection_tasks set dataset"):
            return Result()
        if sql.startswith("insert into collection_events"):
            self.events.append(params)
            return Result()
        if sql.startswith("select id, parent_task_id from collection_tasks"):
            row = self.rows.get(params[0])
            if not row or row["owner_id"] != params[1]:
                return Result()
            return Result({"id": row["id"], "parent_task_id": row["parent_task_id"]})
        if "with recursive chain" in sql:
            root_id = params[0]
            chain = [self.rows[root_id]]
            while True:
                child = next((row for row in self.rows.values() if row["parent_task_id"] == chain[-1]["id"]), None)
                if child is None:
                    break
                chain.append(child)
            return Result(many=[{k: row[k] for k in (
                "id", "owner_id", "prompt", "status", "created_at", "updated_at", "dataset",
                "cancel_requested", "parent_task_id", "version",
            )} for row in chain])
        raise AssertionError(f"Unexpected SQL: {sql}")


@pytest.fixture
def fake_db(monkeypatch):
    db = FakeDatabase()
    db.seed("root")
    monkeypatch.setattr(service_module, "connection", db.connection)
    monkeypatch.setattr(routes.executor, "start", lambda task: None)
    routes.collection_service._tasks.clear()
    return db


def test_rerun_appends_history_and_preserves_parent(fake_db):
    parent_before = dict(fake_db.rows["root"])
    created = [routes.rerun_collection("root", current_user=SimpleNamespace(id="user-1")) for _ in range(3)]
    assert [entry.version for entry in created] == [2, 3, 4]
    assert [entry.parentTaskId for entry in created] == ["root", created[0].taskId, created[1].taskId]
    assert fake_db.rows["root"] == parent_before
    history = routes.get_collection_history("root", SimpleNamespace(id="user-1"))
    assert [entry.version for entry in history] == [1, 2, 3, 4]
    assert [entry.taskId for entry in history] == ["root", *[entry.taskId for entry in created]]


def test_rerun_missing_task_returns_404(fake_db):
    with pytest.raises(HTTPException) as error:
        routes.rerun_collection("missing", current_user=SimpleNamespace(id="user-1"))
    assert error.value.status_code == 404


def test_diff_added_removed_changed(monkeypatch):
    schema = DatasetSchema(name="company", fields=[
        SchemaField(key="name", type="text", label="Name"),
        SchemaField(key="city", type="text", label="City"),
    ])
    before = SimpleNamespace(schema=schema, items=[{"name": "Acme", "city": "Mumbai"}, {"name": "Gone", "city": "Delhi"}])
    after = SimpleNamespace(schema=schema, items=[{"name": "Acme", "city": "Pune"}, {"name": "New", "city": "Chennai"}])
    monkeypatch.setattr(routes.collection_service, "get", lambda task_id, owner: {"old": before, "new": after}.get(task_id))
    result = routes.diff_collections("old", "new", SimpleNamespace(id="user-1"))
    assert result["keyField"] == "name"
    assert result["added"] == [{"name": "New", "city": "Chennai"}]
    assert result["removed"] == [{"name": "Gone", "city": "Delhi"}]
    assert result["changed"][0]["fields"] == ["city"]
