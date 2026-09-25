from typing import List, Optional

from pydantic import BaseModel, Field


class ConversationCreateRequest(BaseModel):
    title: Optional[str] = "New conversation"


class ConversationUpdateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=120)


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
