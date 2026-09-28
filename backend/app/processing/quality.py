"""Deterministic processing (doc §14): validation and deduplication.

Schema-driven validation and canonical deduplication in plain Python.
LLMs should not perform everything — these checks are pure Python so the
pipeline stays reliable, predictable, and reduces unnecessary model calls.
"""

from __future__ import annotations

import re
import urllib.parse
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional, Tuple, Union

from app.schemas.collection import DatasetSchema, SchemaField

_ISO_DATE_REGEX = re.compile(
    r"^(?:\d{4}|\d{4}-\d{2}|\d{4}-\d{2}-\d{2})(?:[T\s].*)?$"
)
_EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@dataclass
class ValidationIssue:
    """A single validation error or warning for a record field."""

    field: str
    rule: str
    severity: Literal["error", "warning"]
    message: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "field": self.field,
            "rule": self.rule,
            "severity": self.severity,
            "message": self.message,
        }


class ValidationResult(list):
    """List of records with attached validation issues and summary metrics.

    Subclasses `list` to preserve backward compatibility for callers expecting `List[dict]`.
    """

    def __init__(
        self,
        records: List[Dict[str, Any]],
        issues: Optional[List[Dict[str, Any]]] = None,
        summary: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(records)
        self.issues: List[Dict[str, Any]] = issues or []
        self.summary: Dict[str, Any] = summary or {}

    def get(self, key: str, default: Any = None) -> Any:
        """Allow dict-like access for callers expecting a result envelope."""
        if key == "records":
            return list(self)
        if key == "issues":
            return self.issues
        if key == "summary":
            return self.summary
        return default


def _extract_schema_and_constraints(
    target: Any,
) -> Tuple[Optional[DatasetSchema], Dict[str, Any]]:
    """Extract DatasetSchema and constraints dict from Requirement, DatasetSchema, or dict."""
    if target is None:
        return None, {}

    # Target is a Requirement object
    if hasattr(target, "schema") and hasattr(target, "constraints"):
        return target.schema, (target.constraints or {})

    # Target is already a DatasetSchema
    if isinstance(target, DatasetSchema):
        return target, {}

    # Target is a dict representing Requirement or Schema
    if isinstance(target, dict):
        if "schema" in target:
            schema_data = target["schema"]
            schema = DatasetSchema(**schema_data) if isinstance(schema_data, dict) else schema_data
            return schema, target.get("constraints", {})
        if "fields" in target:
            return DatasetSchema(**target), {}

    return None, {}


def _is_empty_or_missing(val: Any) -> bool:
    """Return True if value is None, empty string, or whitespace-only."""
    if val is None:
        return True
    if isinstance(val, str) and not val.strip():
        return True
    return False


def _validate_field_type(
    field: SchemaField,
    val: Any,
    constraints: Dict[str, Any],
) -> List[ValidationIssue]:
    """Perform type-based validation on a present field value."""
    issues: List[ValidationIssue] = []
    ftype = (field.type or "text").strip().lower()
    fkey = field.key

    # 1. Currency & Number
    if ftype in ("currency", "number", "integer", "float"):
        if not isinstance(val, (int, float)) or isinstance(val, bool):
            issues.append(
                ValidationIssue(
                    field=fkey,
                    rule="type_number" if ftype != "currency" else "type_currency",
                    severity="error",
                    message=f"Field '{fkey}' must be a numeric value, got {type(val).__name__}",
                )
            )
        else:
            # Check price/currency constraints (e.g. maxPrice)
            max_price = constraints.get("maxPrice") or constraints.get("max_price")
            if max_price is not None and (fkey == "price" or ftype == "currency") and val > max_price:
                issues.append(
                    ValidationIssue(
                        field=fkey,
                        rule="max_price",
                        severity="error",
                        message=f"Field '{fkey}' ({val}) exceeds maximum allowed price ({max_price})",
                    )
                )

    # 2. Rating
    elif ftype == "rating":
        if not isinstance(val, (int, float)) or isinstance(val, bool):
            issues.append(
                ValidationIssue(
                    field=fkey,
                    rule="type_rating",
                    severity="error",
                    message=f"Rating field '{fkey}' must be a numeric value",
                )
            )
        elif not (0 <= val <= 5):
            issues.append(
                ValidationIssue(
                    field=fkey,
                    rule="rating_range",
                    severity="error",
                    message=f"Rating in field '{fkey}' ({val}) must be between 0 and 5",
                )
            )

    # 3. URL / Link / Image
    elif ftype in ("link", "url", "image"):
        val_str = str(val).strip()
        if not val_str.startswith(("https://", "http://")):
            issues.append(
                ValidationIssue(
                    field=fkey,
                    rule="url_format",
                    severity="error",
                    message=f"Field '{fkey}' must be a valid HTTP or HTTPS URL",
                )
            )
        else:
            try:
                parsed = urllib.parse.urlsplit(val_str)
                if not parsed.netloc:
                    issues.append(
                        ValidationIssue(
                            field=fkey,
                            rule="url_format",
                            severity="error",
                            message=f"Field '{fkey}' has invalid URL host/netloc",
                        )
                    )
            except Exception:
                issues.append(
                    ValidationIssue(
                        field=fkey,
                        rule="url_format",
                        severity="error",
                        message=f"Field '{fkey}' has malformed URL",
                    )
                )

    # 4. Date
    elif ftype == "date":
        val_str = str(val).strip()
        if not _ISO_DATE_REGEX.match(val_str):
            issues.append(
                ValidationIssue(
                    field=fkey,
                    rule="date_format",
                    severity="error",
                    message=f"Field '{fkey}' ({val_str}) is not a valid ISO 8601 date (YYYY-MM-DD)",
                )
            )

    # 5. Email
    elif ftype == "email":
        val_str = str(val).strip()
        if not _EMAIL_REGEX.match(val_str):
            issues.append(
                ValidationIssue(
                    field=fkey,
                    rule="email_format",
                    severity="error",
                    message=f"Field '{fkey}' ({val_str}) is not a valid email address",
                )
            )

    # 6. Enum
    elif ftype == "enum" or getattr(field, "options", None):
        options = getattr(field, "options", None)
        if options and val not in options:
            issues.append(
                ValidationIssue(
                    field=fkey,
                    rule="enum_choice",
                    severity="error",
                    message=f"Value '{val}' in field '{fkey}' is not in allowed choices: {options}",
                )
            )

    # 7. Boolean
    elif ftype == "boolean":
        if not isinstance(val, bool):
            issues.append(
                ValidationIssue(
                    field=fkey,
                    rule="type_boolean",
                    severity="error",
                    message=f"Field '{fkey}' must be a boolean",
                )
            )

    # 8. String / Text
    elif ftype in ("text", "string"):
        if not isinstance(val, str):
            issues.append(
                ValidationIssue(
                    field=fkey,
                    rule="type_string",
                    severity="error",
                    message=f"Field '{fkey}' must be a string",
                )
            )

    return issues


def validate_records(
    records: List[Dict[str, Any]],
    requirement: Any,
) -> ValidationResult:
    """Validate records against schema and constraints in plain Python.

    Records with validation errors are flagged with `_is_valid = False` and `_issues`,
    not silently deleted. Returns a `ValidationResult` (subclass of `list`) containing:
    - all validated records (preserving list return type)
    - `.issues`: all issues encountered across records
    - `.summary`: metrics including counts per rule, counts per field, and % complete.
    """
    schema, constraints = _extract_schema_and_constraints(requirement)

    all_issues: List[Dict[str, Any]] = []
    counts_by_rule: Dict[str, int] = defaultdict(int)
    counts_by_field: Dict[str, int] = defaultdict(int)
    counts_by_severity: Dict[str, int] = {"error": 0, "warning": 0}

    fields = schema.fields if schema else []
    required_field_keys = [f.key for f in fields if getattr(f, "required", True)]

    validated_records: List[Dict[str, Any]] = []

    for record in records:
        rec = dict(record)
        rec_issues: List[ValidationIssue] = []

        # 1. Schema-driven checks (if schema provided)
        if fields:
            for field in fields:
                fkey = field.key
                is_req = getattr(field, "required", True)

                # Presence check
                if fkey not in rec or _is_empty_or_missing(rec[fkey]):
                    if is_req:
                        rec_issues.append(
                            ValidationIssue(
                                field=fkey,
                                rule="required",
                                severity="error",
                                message=f"Field '{fkey}' is required but missing or empty",
                            )
                        )
                else:
                    # Type-based check
                    val = rec[fkey]
                    rec_issues.extend(_validate_field_type(field, val, constraints))
        else:
            # Fallback legacy checks if no schema provided
            max_price = constraints.get("maxPrice") or constraints.get("max_price")
            if max_price is not None and "price" in rec:
                if isinstance(rec["price"], (int, float)) and rec["price"] > max_price:
                    rec_issues.append(
                        ValidationIssue(
                            field="price",
                            rule="max_price",
                            severity="error",
                            message=f"price ({rec['price']}) exceeds maxPrice ({max_price})",
                        )
                    )
            if "url" in rec and not str(rec["url"]).startswith(("https://", "http://")):
                rec_issues.append(
                    ValidationIssue(
                        field="url",
                        rule="url_format",
                        severity="error",
                        message="url must start with http:// or https://",
                    )
                )
            if "rating" in rec:
                r_val = rec["rating"]
                if not isinstance(r_val, (int, float)) or not (0 <= r_val <= 5):
                    rec_issues.append(
                        ValidationIssue(
                            field="rating",
                            rule="rating_range",
                            severity="error",
                            message="rating must be between 0 and 5",
                        )
                    )

        # 2. Translate normalization notes into validation issues
        raw_notes = rec.get("_notes", [])
        for note in raw_notes:
            if note == "date_ambiguous":
                rec_issues.append(
                    ValidationIssue(
                        field="date",
                        rule="date_ambiguous",
                        severity="warning",
                        message="Date was resolved from ambiguous format (DD/MM vs MM/DD)",
                    )
                )
            elif note == "currency_unparsed":
                rec_issues.append(
                    ValidationIssue(
                        field="price",
                        rule="currency_unparsed",
                        severity="error",
                        message="Currency/price value could not be parsed",
                    )
                )
            elif note == "number_unparsed":
                rec_issues.append(
                    ValidationIssue(
                        field="number",
                        rule="number_unparsed",
                        severity="error",
                        message="Numeric value could not be parsed",
                    )
                )

        # 3. Flag record (flagged, not deleted)
        issue_dicts = [issue.to_dict() for issue in rec_issues]
        error_count = sum(1 for i in rec_issues if i.severity == "error")
        rec["_issues"] = issue_dicts
        rec["_is_valid"] = (error_count == 0)

        # Tally metrics
        for issue in rec_issues:
            counts_by_rule[issue.rule] += 1
            counts_by_field[issue.field] += 1
            counts_by_severity[issue.severity] += 1
            all_issues.append(issue.to_dict())

        validated_records.append(rec)

    # 4. Calculate summary metrics
    total_records = len(validated_records)
    valid_records = sum(1 for r in validated_records if r.get("_is_valid", True))
    invalid_records = total_records - valid_records

    # Completeness percentage: based on required fields present
    if total_records > 0 and required_field_keys:
        total_required_cells = total_records * len(required_field_keys)
        missing_cells = counts_by_rule.get("required", 0)
        percent_complete = round(
            max(0.0, min(100.0, ((total_required_cells - missing_cells) / total_required_cells) * 100.0)),
            2,
        )
    elif total_records > 0:
        percent_complete = round((valid_records / total_records) * 100.0, 2)
    else:
        percent_complete = 100.0

    summary = {
        "total_records": total_records,
        "valid_records": valid_records,
        "invalid_records": invalid_records,
        "counts_by_rule": dict(counts_by_rule),
        "counts_by_field": dict(counts_by_field),
        "by_rule": dict(counts_by_rule),
        "by_field": dict(counts_by_field),
        "counts_by_severity": counts_by_severity,
        "percent_complete": percent_complete,
    }

    return ValidationResult(validated_records, issues=all_issues, summary=summary)


def record_identity(record: dict) -> Tuple[str, str]:
    """Identity tuple for entity deduplication."""
    return (
        str(record.get("name", record.get("title", ""))).lower(),
        str(record.get("seller", record.get("company", ""))).lower(),
    )


def record_url(record: dict) -> str:
    """Canonical record URL for deduplication."""
    return str(record.get("url", "")).rstrip("/").lower()


def deduplicate_records(
    records: List[dict],
    existing: Optional[List[dict]] = None,
) -> List[dict]:
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
