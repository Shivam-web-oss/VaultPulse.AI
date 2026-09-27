import re
from dataclasses import dataclass

from app.schemas.collection import DatasetSchema, SchemaField


@dataclass
class Requirement:
    entity: str
    entity_label: str
    count: int
    constraints: dict
    schema: DatasetSchema


FIELD_TEMPLATES: dict[str, list[SchemaField]] = {
    "product": [
        SchemaField(key="name", type="text", label="Product"),
        SchemaField(key="price", type="currency", label="Price"),
        SchemaField(key="rating", type="rating", label="Rating"),
        SchemaField(key="image", type="image", label="Image"),
        SchemaField(key="seller", type="text", label="Seller"),
        SchemaField(key="url", type="link", label="Purchase URL"),
    ],
    "job": [
        SchemaField(key="title", type="text", label="Job Title"),
        SchemaField(key="company", type="text", label="Company"),
        SchemaField(key="salary", type="currency", label="Salary"),
        SchemaField(key="experience", type="text", label="Experience"),
        SchemaField(key="location", type="text", label="Location"),
        SchemaField(key="url", type="link", label="Application URL"),
    ],
    "event": [
        SchemaField(key="name", type="text", label="Event"),
        SchemaField(key="date", type="date", label="Date"),
        SchemaField(key="city", type="text", label="City"),
        SchemaField(key="organizer", type="text", label="Organizer"),
        SchemaField(key="url", type="link", label="Registration URL"),
    ],
    "record": [
        SchemaField(key="title", type="text", label="Title"),
        SchemaField(key="description", type="text", label="Description"),
        SchemaField(key="url", type="link", label="Source URL"),
    ],
}

ENTITY_KEYWORDS = {
    "product": ("product", "backpack", "laptop", "phone", "shoe", "buy", "price", "purchase", "sell"),
    "job": ("job", "jobs", "hiring", "position", "vacancy", "developer", "engineer", "resume"),
    "event": ("event", "conference", "meetup", "summit", "hackathon", "webinar", "expo"),
}

DEFAULT_COUNT = 20
MAX_COUNT = 200
# Fake sources run out below this ceiling, which exercises the PARTIAL path.
SOURCE_CEILING = 50


def _detect_entity(prompt: str) -> str:
    lowered = prompt.lower()
    for entity, keywords in ENTITY_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            return entity
    return "record"


def _extract_count(prompt: str) -> int:
    match = re.search(r"\b(?:find|top|get|show|list|collect)?\s*(\d{1,4})\b", prompt, re.IGNORECASE)
    if match is None:
        return DEFAULT_COUNT
    return max(1, min(int(match.group(1)), MAX_COUNT))


def _extract_constraints(prompt: str) -> dict:
    constraints: dict = {}
    price_match = re.search(r"(?:under|below|less than|<)\s*(?:₹|rs\.?|inr)?\s*([\d,]+)", prompt, re.IGNORECASE)
    if price_match:
        constraints["maxPrice"] = int(price_match.group(1).replace(",", ""))
        constraints["currency"] = "INR"
    location_match = re.search(r"\bin\s+([A-Z][A-Za-z]+(?:\s[A-Z][A-Za-z]+)?)", prompt)
    if location_match:
        constraints["location"] = location_match.group(1)
    return constraints


def _requested_fields(prompt: str, fields: list[SchemaField]) -> list[SchemaField]:
    match = re.search(r"\bwith\b(.+)$", prompt, re.IGNORECASE)
    if match is None:
        return fields
    requested = match.group(1).lower()
    selected = [field for field in fields if field.label.lower() in requested or field.key in requested]
    link_fields = [field for field in fields if field.type == "link"]
    return selected + [field for field in link_fields if field not in selected] or fields


def analyze(prompt: str) -> Requirement:
    entity = _detect_entity(prompt)
    fields = FIELD_TEMPLATES.get(entity, FIELD_TEMPLATES["record"])
    return Requirement(
        entity=entity,
        entity_label=entity.capitalize(),
        count=_extract_count(prompt),
        constraints=_extract_constraints(prompt),
        schema=DatasetSchema(name=entity, version="1.0", fields=_requested_fields(prompt, fields)),
    )
