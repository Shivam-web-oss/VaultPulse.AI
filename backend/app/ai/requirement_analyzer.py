import logging
import re
from dataclasses import dataclass

from pydantic import ValidationError

from app.schemas.collection import DatasetSchema, SchemaField

logger = logging.getLogger(__name__)


@dataclass
class Requirement:
    entity: str
    entity_label: str
    count: int
    constraints: dict
    schema: DatasetSchema
    search_terms: str = ""


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


_SEARCH_STOPWORDS = re.compile(
    r"\b(?:find|get|show|list|collect|give|me|the|a|an|about|for|from|with|top|latest|"
    r"articles?|news|records?|items?|entries?|pages?|products?|jobs?|events?|under|below|less|than|in)\b|\d+",
    re.IGNORECASE,
)


def _extract_search_terms(prompt: str) -> str:
    """Reduce the prompt to the topic words worth sending to a search API.

    Deterministic and independent of which requirement analyzer (LLM or
    regex) determined the entity/schema -- both paths call this on the same
    raw prompt, so search terms never disagree with which analyzer ran.
    """
    cleaned = _SEARCH_STOPWORDS.sub(" ", prompt)
    terms = " ".join(cleaned.split())
    return terms[:200]


def _analyze_regex(prompt: str) -> Requirement:
    """Deterministic keyword/regex analysis (Phase C). Kept as the fallback

    path for when the LLM analyzer is unconfigured, unreachable, or returns
    output that fails validation -- see `analyze()` below.
    """
    entity = _detect_entity(prompt)
    fields = FIELD_TEMPLATES.get(entity, FIELD_TEMPLATES["record"])
    return Requirement(
        entity=entity,
        entity_label=entity.capitalize(),
        count=_extract_count(prompt),
        constraints=_extract_constraints(prompt),
        schema=DatasetSchema(name=entity, version="1.0", fields=_requested_fields(prompt, fields)),
        search_terms=_extract_search_terms(prompt),
    )


def analyze(prompt: str) -> Requirement:
    """Understand a natural-language data request (Phase D.5, doc SS11/SS12).

    Tries the LLM-based analyzer first, which can understand arbitrary
    entities and propose their own field schema rather than being limited to
    the hardcoded product/job/event templates below. Any failure -- provider
    unconfigured or unreachable, non-JSON output, or output that fails the
    field-type/field-count/record-count validation in
    `app.ai.llm_requirement_analyzer` -- falls back to the deterministic
    regex analyzer so the pipeline always produces a usable requirement.

    `search_terms` is always derived deterministically from the raw prompt
    (Phase D's clean-search-term step), regardless of which analyzer path
    ran, so the search API query never disagrees with how the requirement
    was understood.
    """
    search_terms = _extract_search_terms(prompt)

    try:
        from app.ai.llm_requirement_analyzer import LLMUnavailableError, analyze_with_llm

        result = analyze_with_llm(prompt)
    except (LLMUnavailableError, ValidationError) as error:
        logger.info("requirement_analyzer.llm_fallback reason=%s: %s", type(error).__name__, error)
        return _analyze_regex(prompt)
    except Exception as error:  # noqa: BLE001 - this step must never crash the pipeline
        logger.warning("requirement_analyzer.llm_unexpected_error reason=%s: %s", type(error).__name__, error)
        return _analyze_regex(prompt)

    return Requirement(
        entity=result.entity,
        entity_label=result.entityLabel,
        count=result.count,
        constraints=result.constraints,
        schema=DatasetSchema(name=result.entity, version="1.0", fields=result.fields),
        search_terms=search_terms,
    )