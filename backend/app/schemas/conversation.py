from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class ConversationCreateRequest(BaseModel):
    title: Optional[str] = "New conversation"

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        normalized = value.strip()
        if not normalized:
            raise ValueError("title must contain non-whitespace characters")
        return normalized


class ConversationUpdateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=120)

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("title must contain non-whitespace characters")
        return normalized


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    created_at: str


class ConversationOut(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str


class ConversationDetailOut(ConversationOut):
    messages: List[MessageOut] = Field(default_factory=list)
