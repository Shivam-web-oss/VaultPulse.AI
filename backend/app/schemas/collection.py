from datetime import datetime
from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class TaskStatus(str, Enum):
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class CollectionCreateRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=4000)

    @field_validator("prompt")
    @classmethod
    def validate_prompt(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("prompt must contain non-whitespace characters")
        return normalized


class CollectionCreatedResponse(BaseModel):
    taskId: str
    status: TaskStatus = TaskStatus.CREATED


class SchemaField(BaseModel):
    key: str = Field(min_length=1, max_length=80)
    type: str = Field(min_length=1, max_length=40)
    label: str = Field(min_length=1, max_length=120)

    @field_validator("key", "type", "label")
    @classmethod
    def validate_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("schema field values must contain non-whitespace characters")
        return normalized


class DatasetSchema(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    version: str = "1.0"
    fields: list[SchemaField] = Field(default_factory=list)


class DatasetData(BaseModel):
    count: int = Field(default=0, ge=0)
    items: list[dict[str, Any]] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_count(self):
        if self.count != len(self.items):
            raise ValueError("data.count must equal the number of data.items")
        return self


class ProvenanceEntry(BaseModel):
    recordIndex: int = Field(ge=0)
    sourceUrl: str
    sourceName: str
    retrievedAt: datetime


class DatasetProvenance(BaseModel):
    retrievedAt: datetime
    entries: list[ProvenanceEntry] = Field(default_factory=list)


class DatasetView(BaseModel):
    suggestedType: Optional[str] = None


class Dataset(BaseModel):
    request: CollectionCreateRequest
    view: DatasetView = DatasetView()
    schema_: DatasetSchema = Field(alias="schema", default_factory=DatasetSchema)
    data: DatasetData = Field(default_factory=DatasetData)
    provenance: DatasetProvenance

    model_config = {"populate_by_name": True}


class CollectionStatusResponse(BaseModel):
    taskId: str
    status: TaskStatus
    prompt: str
    createdAt: datetime
    updatedAt: datetime
    recordCount: int


class CollectionResultResponse(BaseModel):
    request: dict[str, Any]
    dataset: Dataset
    ui: dict[str, Any]
    provenance: list[ProvenanceEntry]
    files: dict[str, str]


class CancelResponse(BaseModel):
    taskId: str
    status: TaskStatus
    cancelled: bool
