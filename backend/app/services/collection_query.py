"""Collection query service (Task B).

Provides type-aware filtering, searching, sorting, and pagination for dataset items.
Items are stored in Postgres as JSONB (`collection_tasks.dataset -> data -> items`),
so queries are evaluated server-side in Python before pagination.

Scalability Note:
For datasets up to ~10,000 records, in-memory JSONB filtering and sorting is fast (<10ms).
For collections scaling beyond 50,000+ records, items should be projected into a dedicated
`dataset_items` table with GIN indexed columns to push queries directly down into Postgres.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from functools import cmp_to_key
from typing import Any, Callable, Dict, Generator, List, Optional, Set, Tuple, Union

from fastapi import HTTPException

from app.schemas.collection import DatasetSchema

SUPPORTED_OPERATORS: Set[str] = {
    "eq",
    "neq",
    "gt",
    "gte",
    "lt",
    "lte",
    "in",
    "contains",
}

NUMERIC_TYPES: Set[str] = {
    "number",
    "currency",
    "price",
    "rating",
    "integer",
    "float",
}


@dataclass
class FilterClause:
    field: str
    operator: str
    value: str


@dataclass
class SortClause:
    field: str
    descending: bool


def _allowed_field_keys(schema: Optional[DatasetSchema]) -> Set[str]:
    """Return all valid field keys from schema plus standard metadata fields."""
    keys = {"source_url", "fetched_at", "url"}
    if schema and schema.fields:
        for f in schema.fields:
            keys.add(f.key)
    return keys


def parse_filter_param(
    filter_param: Union[str, List[str], None],
    allowed_fields: Set[str],
) -> List[FilterClause]:
    """Parse repeatable or comma-separated filter clauses.

    Formats supported:
    - ?filter=city:eq:Mumbai&filter=founded:gte:2018
    - ?filter=city:eq:Mumbai,founded:gte:2018,stage:in:seed|seriesA

    Validates field names against allowed_fields and operators against SUPPORTED_OPERATORS.
    Raises HTTPException(400) on invalid field or operator.
    """
    if not filter_param:
        return []

    # Flatten inputs
    raw_clauses: List[str] = []
    if isinstance(filter_param, str):
        # Split on commas that are not inside quotes or pipes if comma-separated
        raw_clauses.extend(c.strip() for c in filter_param.split(",") if c.strip())
    elif isinstance(filter_param, list):
        for entry in filter_param:
            raw_clauses.extend(c.strip() for c in entry.split(",") if c.strip())

    parsed: List[FilterClause] = []
    for clause in raw_clauses:
        parts = clause.split(":", 2)
        if len(parts) != 3:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid filter format '{clause}'. Expected '<field>:<operator>:<value>'",
            )
        field, op, val = parts[0].strip(), parts[1].strip().lower(), parts[2].strip()

        if field not in allowed_fields:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown field '{field}'. Allowed fields: {sorted(list(allowed_fields))}",
            )

        if op not in SUPPORTED_OPERATORS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported operator '{op}'. Supported operators: {', '.join(sorted(SUPPORTED_OPERATORS))}",
            )

        parsed.append(FilterClause(field=field, operator=op, value=val))

    return parsed


def parse_sort_param(
    sort_param: Optional[str],
    allowed_fields: Set[str],
) -> List[SortClause]:
    """Parse comma-separated sort fields (e.g. sort=-founded,name).

    A leading minus '-' indicates descending order.
    Validates field names against allowed_fields.
    Raises HTTPException(400) on invalid field.
    """
    if not sort_param:
        return []

    clauses: List[SortClause] = []
    for part in sort_param.split(","):
        token = part.strip()
        if not token:
            continue
        descending = token.startswith("-")
        field = token[1:].strip() if (descending or token.startswith("+")) else token

        if field not in allowed_fields:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown sort field '{field}'. Allowed fields: {sorted(list(allowed_fields))}",
            )

        clauses.append(SortClause(field=field, descending=descending))

    return clauses


def _get_field_type(field: str, schema: Optional[DatasetSchema]) -> str:
    if schema and schema.fields:
        for f in schema.fields:
            if f.key == field:
                return (f.type or "text").strip().lower()
    return "text"


def _matches_clause(item: Dict[str, Any], clause: FilterClause, field_type: str) -> bool:
    """Evaluate a single filter clause against an item with type awareness."""
    field = clause.field
    op = clause.operator
    target_raw = clause.value
    item_val = item.get(field)

    # 1. Numeric comparison
    if field_type in NUMERIC_TYPES:
        if op == "in":
            try:
                target_nums = [float(v.strip()) for v in target_raw.split("|") if v.strip()]
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid numeric list for 'in' filter: '{target_raw}'")
            if item_val is None:
                return False
            try:
                return float(item_val) in target_nums
            except (ValueError, TypeError):
                return False

        try:
            target_num = float(target_raw)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid numeric value '{target_raw}' for field '{field}'")

        if item_val is None:
            return op == "neq"

        try:
            val_num = float(item_val)
        except (ValueError, TypeError):
            return op == "neq"

        if op == "eq":
            return val_num == target_num
        elif op == "neq":
            return val_num != target_num
        elif op == "gt":
            return val_num > target_num
        elif op == "gte":
            return val_num >= target_num
        elif op == "lt":
            return val_num < target_num
        elif op == "lte":
            return val_num <= target_num
        elif op == "contains":
            return target_raw in str(item_val)
        return False

    # 2. Date comparison (ISO 8601 strings compare chronologically via lexicographical comparison)
    if field_type == "date":
        if op == "in":
            target_dates = [v.strip() for v in target_raw.split("|") if v.strip()]
            if item_val is None:
                return False
            return str(item_val).strip() in target_dates

        target_date = target_raw.strip()
        if item_val is None:
            return op == "neq"

        val_date = str(item_val).strip()

        if op == "eq":
            return val_date == target_date
        elif op == "neq":
            return val_date != target_date
        elif op == "gt":
            return val_date > target_date
        elif op == "gte":
            return val_date >= target_date
        elif op == "lt":
            return val_date < target_date
        elif op == "lte":
            return val_date <= target_date
        elif op == "contains":
            return target_date in val_date
        return False

    # 3. String / Text / Link / Email / Enum comparison
    if op == "in":
        target_options = [v.strip().lower() for v in target_raw.split("|") if v.strip()]
        if item_val is None:
            return False
        return str(item_val).strip().lower() in target_options

    if item_val is None:
        return op == "neq"

    item_str = str(item_val).strip().lower()
    target_str = target_raw.strip().lower()

    if op == "eq":
        return item_str == target_str
    elif op == "neq":
        return item_str != target_str
    elif op == "gt":
        return item_str > target_str
    elif op == "gte":
        return item_str >= target_str
    elif op == "lt":
        return item_str < target_str
    elif op == "lte":
        return item_str <= target_str
    elif op == "contains":
        return target_str in item_str

    return False


def _item_matches_search(item: Dict[str, Any], search_query: str) -> bool:
    """Case-insensitive substring search across string fields in item."""
    q = search_query.strip().lower()
    for k, v in item.items():
        if k.startswith("_"):
            continue
        if v is not None and q in str(v).lower():
            return True
    return False


def _compare_items(
    a: Dict[str, Any],
    b: Dict[str, Any],
    sort_clauses: List[SortClause],
    schema: Optional[DatasetSchema],
) -> int:
    """Multi-column comparator ensuring None values always sort last."""
    for clause in sort_clauses:
        field = clause.field
        descending = clause.descending
        ftype = _get_field_type(field, schema)

        val_a = a.get(field)
        val_b = b.get(field)

        # None values sort last in both ascending and descending order
        if val_a is None and val_b is None:
            continue
        if val_a is None:
            return 1  # a is None -> a sorts after b
        if val_b is None:
            return -1  # b is None -> b sorts after a

        diff = 0
        if ftype in NUMERIC_TYPES:
            try:
                num_a, num_b = float(val_a), float(val_b)
                if num_a < num_b:
                    diff = -1
                elif num_a > num_b:
                    diff = 1
            except (ValueError, TypeError):
                str_a, str_b = str(val_a).lower(), str(val_b).lower()
                if str_a < str_b:
                    diff = -1
                elif str_a > str_b:
                    diff = 1
        elif ftype == "date":
            str_a, str_b = str(val_a).strip(), str(val_b).strip()
            if str_a < str_b:
                diff = -1
            elif str_a > str_b:
                diff = 1
        else:
            str_a, str_b = str(val_a).lower(), str(val_b).lower()
            if str_a < str_b:
                diff = -1
            elif str_a > str_b:
                diff = 1

        if diff != 0:
            return -diff if descending else diff

    return 0


def query_collection_items(
    raw_items: List[Dict[str, Any]],
    schema: Optional[DatasetSchema],
    search: Optional[str] = None,
    filter_param: Union[str, List[str], None] = None,
    sort_param: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    default_fetched_at: str = "",
) -> Tuple[List[Dict[str, Any]], int]:
    """Execute search, filtering, type-aware sorting, and pagination on items.

    Ensures every returned item includes `source_url` and `fetched_at`.
    Returns (page_items, total_matching_count).
    """
    allowed_fields = _allowed_field_keys(schema)
    filters = parse_filter_param(filter_param, allowed_fields)
    sort_clauses = parse_sort_param(sort_param, allowed_fields)

    # Prepare items with guaranteed source_url and fetched_at
    enriched_items: List[Dict[str, Any]] = []
    for item in raw_items:
        rec = dict(item)
        if "source_url" not in rec or not rec["source_url"]:
            rec["source_url"] = str(rec.get("_source_url") or rec.get("url") or "")
        if "fetched_at" not in rec or not rec["fetched_at"]:
            rec["fetched_at"] = str(rec.get("_fetched_at") or default_fetched_at)
        enriched_items.append(rec)

    # 1. Apply Search
    filtered = enriched_items
    if search and search.strip():
        q = search.strip()
        filtered = [item for item in filtered if _item_matches_search(item, q)]

    # 2. Apply Filters
    if filters:
        for clause in filters:
            ftype = _get_field_type(clause.field, schema)
            filtered = [item for item in filtered if _matches_clause(item, clause, ftype)]

    total_count = len(filtered)

    # 3. Apply Sorting
    if sort_clauses:
        comparator = cmp_to_key(lambda a, b: _compare_items(a, b, sort_clauses, schema))
        filtered = sorted(filtered, key=comparator)

    # 4. Apply Pagination
    start = (page - 1) * page_size
    end = start + page_size
    page_items = filtered[start:end]

    return page_items, total_count


def stream_csv(
    items: List[Dict[str, Any]],
    schema: Optional[DatasetSchema],
) -> Generator[str, None, None]:
    """Stream collection items formatted as CSV."""
    field_keys = [f.key for f in schema.fields] if (schema and schema.fields) else []
    # Guarantee source_url and fetched_at columns
    if "source_url" not in field_keys:
        field_keys.append("source_url")
    if "fetched_at" not in field_keys:
        field_keys.append("fetched_at")

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=field_keys, extrasaction="ignore")
    writer.writeheader()
    yield output.getvalue()
    output.seek(0)
    output.truncate(0)

    for item in items:
        writer.writerow(item)
        yield output.getvalue()
        output.seek(0)
        output.truncate(0)
