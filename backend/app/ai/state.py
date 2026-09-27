"""LangGraph collection state (doc §11)."""

from typing import Annotated, List, TypedDict

from app.schemas.collection import ProvenanceEntry


def _append(current: List, additions: List) -> List:
    return [*current, *additions]


class CollectionState(TypedDict):
    prompt: str

    # Planning outputs
    requirement: dict
    workflow: dict
    sources: List[str]
    tool_calls: List[dict]

    # Collection outputs (append-only across loop iterations)
    raw_evidence: Annotated[List[dict], _append]
    extracted_records: Annotated[List[dict], _append]
    provenance_entries: Annotated[List[ProvenanceEntry], _append]

    # Processing outputs (recomputed each pass)
    normalized_records: List[dict]
    valid_records: List[dict]
    final_records: List[dict]

    schema: dict
    view: dict

    target_count: int
    current_count: int
    round: int

    status: str
    errors: List[str]
