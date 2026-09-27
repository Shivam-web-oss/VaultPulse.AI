"""Deterministic processing (doc §14): validation and deduplication.

LLMs should not perform everything — these checks are plain Python so the
pipeline stays reliable and reduces unnecessary model calls.
"""

from typing import List, Tuple

from app.ai.requirement_analyzer import Requirement


def validate_records(records: List[dict], requirement: Requirement) -> List[dict]:
    max_price = requirement.constraints.get("maxPrice")
    valid = []
    for record in records:
        if max_price is not None and "price" in record and record["price"] > max_price:
            continue
        if "url" in record and not str(record["url"]).startswith("https://"):
            continue
        if "rating" in record and not 0 <= record["rating"] <= 5:
            continue
        valid.append(record)
    return valid


def record_identity(record: dict) -> Tuple[str, str]:
    return (
        str(record.get("name", record.get("title", ""))).lower(),
        str(record.get("seller", record.get("company", ""))).lower(),
    )


def record_url(record: dict) -> str:
    return str(record.get("url", "")).rstrip("/").lower()


def deduplicate_records(records: List[dict], existing: List[dict] = None) -> List[dict]:
    """Canonical URL first, then name+seller identity (doc §14).

    `existing` holds records from earlier rounds; they are kept as-is and
    only used to suppress duplicates in `records`.
    """
    existing = existing or []
    seen_urls = {record_url(record) for record in existing if record.get("url")}
    seen_identity = {record_identity(record) for record in existing}
    unique = list(existing)
    for record in records:
        url = record_url(record)
        identity = record_identity(record)
        if url and url in seen_urls:
            continue
        if identity in seen_identity:
            continue
        seen_urls.add(url)
        seen_identity.add(identity)
        unique.append(record)
    return unique
