"""Deterministic fake collector for Phase B.

Generates plausible records for the requested entity without any network
access. Record values are derived from the requirement so the same prompt
always produces the same dataset, which keeps API contract tests stable.
"""

from typing import Iterator

from app.ai.requirement_analyzer import Requirement, SOURCE_CEILING
from app.schemas.collection import ProvenanceEntry

_PRODUCT_NAMES = (
    "Trail Pack", "Campus Backpack", "Urban Daypack", "Summit Rucksack", "Commuter Bag",
    "Study Satchel", "Field Kit Pack", "Metro Carrier", "Ridge Pack", "Campus Classic",
)
_SELLERS = ("CampusMart", "BagBazaar", "PackPoint", "StudentStore", "DealDen")
_JOB_TITLES = ("Spring Boot Developer", "Backend Engineer", "Java Developer", "Platform Engineer", "API Developer")
_COMPANIES = ("InfoEdge Systems", "CloudNine Tech", "NimbusSoft", "QuantumWorks", "DataBridge")
_EVENT_NAMES = ("India Tech Summit", "DevCon Bengaluru", "AI Expo India", "Cloud Summit", "StartupX Conference")
_ORGANIZERS = ("TechEvents India", "DevCommunity", "GlobalConferences", "Eventra", "SummitWorks")
_CITIES = ("Bengaluru", "Mumbai", "Hyderabad", "Pune", "Delhi", "Chennai")

_NAMES = {"product": _PRODUCT_NAMES, "job": _JOB_TITLES, "event": _EVENT_NAMES}
_RECORD_TYPES = {"product": "product", "job": "job", "event": "event", "record": "article"}


def _requested_count(requirement: Requirement) -> int:
    # Fake sources hold a limited pool, so large requests exercise the PARTIAL path.
    return min(requirement.count, SOURCE_CEILING)


def _name(requirement: Requirement, index: int) -> str:
    names = _NAMES.get(requirement.entity, ("Guide", "Overview", "Handbook", "Report", "Primer"))
    base = names[index % len(names)]
    suffix = index // len(names) + 1
    return f"{base} {suffix}" if suffix > 1 else base


def _record(entity: str, index: int, requirement: Requirement) -> dict:
    name = _name(requirement, index)
    if entity == "product":
        max_price = requirement.constraints.get("maxPrice")
        ceiling = max_price if max_price is not None else 5000
        price = max(299, (ceiling - 150) - (index * 37) % max(1, ceiling - 400))
        return {
            "name": name,
            "price": price,
            "currency": requirement.constraints.get("currency", "INR"),
            "rating": round(3.4 + (index * 17 % 16) / 10, 1),
            "image": f"https://images.example.com/{entity}/{index + 1}.jpg",
            "seller": _SELLERS[index % len(_SELLERS)],
            "url": f"https://shop.example.com/{entity}/{index + 1}",
        }
    if entity == "job":
        return {
            "title": name,
            "company": _COMPANIES[index % len(_COMPANIES)],
            "salary": 400000 + (index * 45000) % 900000,
            "currency": "INR",
            "experience": f"{1 + index % 6}-{3 + index % 6} years",
            "location": requirement.constraints.get("location", _CITIES[index % len(_CITIES)]),
            "url": f"https://jobs.example.com/{index + 1}",
        }
    if entity == "event":
        return {
            "name": name,
            "date": f"2026-{10 + index % 3:02d}-{1 + index % 28:02d}",
            "city": requirement.constraints.get("location", _CITIES[index % len(_CITIES)]),
            "organizer": _ORGANIZERS[index % len(_ORGANIZERS)],
            "url": f"https://events.example.com/{index + 1}",
        }
    return {
        "title": name,
        "description": f"Collected reference material {index + 1} for: {requirement.entity_label}",
        "url": f"https://sources.example.com/{index + 1}",
    }


def collect(requirement: Requirement) -> Iterator[tuple[dict, ProvenanceEntry]]:
    """Yield (record, provenance) pairs for the analyzed requirement."""
    entity = _RECORD_TYPES.get(requirement.entity, "article")
    total = _requested_count(requirement)
    for index in range(total):
        record = _record(requirement.entity, index, requirement)
        yield record, ProvenanceEntry(
            recordIndex=index,
            sourceUrl=str(record.get("url", "")),
            sourceName=f"Example {entity} directory",
            retrievedAt=_pseudo_timestamp(index),
        )


def _pseudo_timestamp(index: int) -> str:
    from datetime import datetime, timedelta, timezone

    base = datetime.now(timezone.utc).replace(microsecond=0)
    return (base - timedelta(minutes=index)).isoformat()
