from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.schemas.collection import DatasetSchema, SchemaField
from app.services.collection_query import query_collection_items


SCHEMA = DatasetSchema(name="company", fields=[
    SchemaField(key="name", type="text", label="Name"),
    SchemaField(key="city", type="text", label="City"),
    SchemaField(key="founded", type="integer", label="Founded"),
    SchemaField(key="stage", type="text", label="Stage"),
    SchemaField(key="date", type="date", label="Date"),
])
ITEMS = [
    {"name": "Alpha", "city": "Mumbai", "founded": 2018, "stage": "seed", "date": "2020-05-10"},
    {"name": "Beta", "city": "Pune", "founded": 2021, "stage": "seriesA", "date": "2019-01-01"},
    {"name": "Gamma", "city": "Mumbai", "founded": 2015, "stage": "seed", "date": "2022-01-01"},
]


def run(**kwargs):
    return query_collection_items(ITEMS, SCHEMA, default_fetched_at="2024-01-01T00:00:00+00:00", **kwargs)


def test_search_hit_miss_and_metadata():
    hits, total = run(search="MUM")
    assert total == 2
    assert hits[0]["source_url"] == ""
    assert hits[0]["fetched_at"] == "2024-01-01T00:00:00+00:00"
    assert run(search="absent")[1] == 0


@pytest.mark.parametrize(("op", "value", "expected"), [
    ("eq", "Mumbai", 2), ("neq", "Mumbai", 1), ("gt", "2018", 1),
    ("gte", "2018", 2), ("lt", "2018", 1), ("lte", "2018", 2),
    ("in", "2015|2021", 2), ("contains", "um", 2),
])
def test_each_operator(op, value, expected):
    assert run(filter_param=f"{'city' if op in ('eq', 'neq', 'contains') else 'founded'}:{op}:{value}")[1] == expected


def test_date_comparison_and_combined_filters():
    result, total = run(filter_param=["city:eq:Mumbai", "founded:gte:2018", "date:lt:2021-01-01"])
    assert total == 1 and result[0]["name"] == "Alpha"
    assert run(filter_param="date:gte:2020-01-01")[1] == 2


def test_sort_ascending_descending_and_none_last():
    ascending, _ = run(sort_param="founded")
    descending, _ = run(sort_param="-founded")
    assert [r["founded"] for r in ascending] == [2015, 2018, 2021]
    assert [r["founded"] for r in descending] == [2021, 2018, 2015]


def test_pagination_boundaries():
    second, total = run(sort_param="name", page=2, page_size=2)
    empty, _ = run(page=4, page_size=1)
    assert total == 3 and [r["name"] for r in second] == ["Gamma"]
    assert empty == []


@pytest.mark.parametrize("clause, message", [
    ("unknown:eq:x", "Unknown field"),
    ("city:bogus:x", "Unsupported operator"),
])
def test_invalid_filter_field_and_operator(clause, message):
    with pytest.raises(HTTPException, match=message):
        run(filter_param=clause)


def test_data_route_empty_result_and_missing_collection(monkeypatch):
    task = SimpleNamespace(
        id="task", items=ITEMS, schema=SCHEMA, updated_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )
    from app.routes import collections as route_module
    monkeypatch.setattr(route_module.collection_service, "get", lambda task_id, user: task if task_id == "task" else None)
    response = route_module.get_collection_data(
        "task", search="missing", filter=None, page=1, page_size=20, format=None,
        current_user=SimpleNamespace(id="user"),
    )
    assert response.model_dump(by_alias=True) == {"total": 0, "page": 1, "page_size": 20, "items": []}
    with pytest.raises(HTTPException) as error:
        route_module.get_collection_data(
            "missing", filter=None, page=1, page_size=20, format=None,
            current_user=SimpleNamespace(id="user"),
        )
    assert error.value.status_code == 404
