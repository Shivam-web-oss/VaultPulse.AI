"""LLM-based requirement understanding (Phase D.5, doc §11/§12).

Calls the same OpenAI-compatible chat provider used by `chat_service` to turn
an arbitrary natural-language data request into a structured requirement:
entity, target count, constraints, and a dataset field schema. The LLM may
propose *any* entity and field set — it is not limited to the old
product/job/event templates — but every response is re-validated against a
strict Pydantic model (field-type whitelist, field-count ceiling, count
ceiling) before it is trusted.

This module never raises past its own boundary in a way that could stall the
pipeline: any failure (provider unavailable, bad JSON, failed validation)
surfaces as `LLMUnavailableError` or `pydantic.ValidationError`, and the only
caller (`app.ai.requirement_analyzer.analyze`) catches both and falls back to
the deterministic regex analyzer. Nothing here fabricates a result.
"""

import json
import logging
import os
from typing import List, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pydantic import BaseModel, Field, field_validator

from app.schemas.collection import SchemaField

logger = logging.getLogger(__name__)

# Keep this in sync with whatever field renderers the dashboard actually
# supports. Anything outside this whitelist is rejected, not coerced.
ALLOWED_FIELD_TYPES = {"text", "currency", "rating", "image", "link", "date", "number", "boolean"}
MIN_FIELDS = 1
MAX_FIELDS = 8
MAX_COUNT = 200
REQUEST_TIMEOUT_SECONDS = 20

_SYSTEM_PROMPT = (
    "You are the requirement-understanding stage of a data collection pipeline. "
    "Read the user's natural-language data request and respond with ONLY a single "
    "JSON object (no prose, no markdown fences, no code blocks) with exactly these keys:\n\n"
    '- "entity": a short lowercase snake_case slug naming what is being collected '
    '(e.g. "product", "job", "rental_listing", "research_paper"). Invent a new slug '
    "if none of the obvious ones fit — do not force the request into a category it isn't.\n"
    '- "entityLabel": a human-readable label for the entity (e.g. "Rental Listing").\n'
    '- "count": integer, how many records the user wants. Default to 20 if unspecified. '
    f"Never exceed {MAX_COUNT}.\n"
    '- "constraints": an object of any filters mentioned in the request (e.g. maxPrice, '
    "location, currency, dateRange) — an empty object if none were mentioned. Do not invent "
    "constraints the user didn't state.\n"
    f'- "fields": an array of {MIN_FIELDS} to {MAX_FIELDS} field objects describing the dataset '
    'columns. Each field object has "key" (short lowercase identifier, no spaces), "type" '
    f'(one of: {", ".join(sorted(ALLOWED_FIELD_TYPES))}), and "label" (human-readable column name). '
    'Always include exactly one field with key "url" and type "link" pointing to the record\'s '
    "source page, since every record must be traceable to where it came from.\n\n"
    "Respond with valid JSON only — nothing before or after it."
)


class LLMRequirementResponse(BaseModel):
    entity: str = Field(min_length=1, max_length=60)
    entityLabel: str = Field(min_length=1, max_length=120)
    count: int = Field(ge=1, le=MAX_COUNT)
    constraints: dict = Field(default_factory=dict)
    fields: List[SchemaField] = Field(min_length=MIN_FIELDS, max_length=MAX_FIELDS)

    @field_validator("entity")
    @classmethod
    def _slugify_entity(cls, value: str) -> str:
        normalized = value.strip().lower().replace(" ", "_").replace("-", "_")
        if not normalized or not all(ch.isalnum() or ch == "_" for ch in normalized):
            raise ValueError("entity must be a simple lowercase slug (letters, digits, underscores)")
        return normalized

    @field_validator("fields")
    @classmethod
    def _check_fields(cls, value: List[SchemaField]) -> List[SchemaField]:
        for field in value:
            if field.type not in ALLOWED_FIELD_TYPES:
                raise ValueError(f"unsupported field type: {field.type!r}")
        if not any(field.key == "url" for field in value):
            # Provenance matching keys off the "url" field downstream (see
            # `app.workflow.executor._match_provenance`) — never lose it silently.
            if len(value) >= MAX_FIELDS:
                value = value[: MAX_FIELDS - 1]
            value = [*value, SchemaField(key="url", type="link", label="Source URL")]
        return value


class LLMUnavailableError(RuntimeError):
    """Raised for any condition that should trigger the regex fallback."""


def _provider_config() -> Optional[dict]:
    provider_name = os.getenv("AI_PROVIDER", "unconfigured").strip().lower()
    if provider_name not in {"openai", "openai-compatible"}:
        return None
    api_key = os.getenv("AI_PROVIDER_API_KEY", "").strip()
    if not api_key:
        return None
    return {
        "api_key": api_key,
        "base_url": os.getenv("AI_PROVIDER_BASE_URL", "https://api.openai.com/v1/chat/completions").strip(),
        "model": os.getenv("AI_MODEL", "gpt-4o-mini").strip(),
    }


def _call_provider(prompt: str) -> str:
    config = _provider_config()
    if config is None:
        raise LLMUnavailableError("AI provider is not configured")

    payload = json.dumps({
        "model": config["model"],
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0,
    }).encode("utf-8")
    request = Request(
        config["base_url"],
        data=payload,
        headers={"Authorization": f"Bearer {config['api_key']}", "Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            result = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
        raise LLMUnavailableError("AI provider request failed") from error

    try:
        content = result["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as error:
        raise LLMUnavailableError("AI provider returned an unexpected response shape") from error
    if not isinstance(content, str) or not content.strip():
        raise LLMUnavailableError("AI provider returned an empty response")
    return content.strip()


def _strip_code_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text[:4].lower() == "json":
            text = text[4:]
    return text.strip()


def analyze_with_llm(prompt: str) -> LLMRequirementResponse:
    """Turn a raw prompt into a validated `LLMRequirementResponse`.

    Raises `LLMUnavailableError` (provider unreachable/misconfigured, bad or
    non-JSON output) or `pydantic.ValidationError` (well-formed JSON that
    fails schema/type/count checks). Callers must catch both and fall back —
    this function never returns a partially-trusted result.
    """
    raw = _call_provider(prompt)
    cleaned = _strip_code_fence(raw)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as error:
        raise LLMUnavailableError("AI provider did not return valid JSON") from error
    return LLMRequirementResponse.model_validate(data)