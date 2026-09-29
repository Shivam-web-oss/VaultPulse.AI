from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class MessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=20000)
    client_message_id: Optional[UUID] = None

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("message must contain non-whitespace characters")
        return normalized


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    created_at: str
