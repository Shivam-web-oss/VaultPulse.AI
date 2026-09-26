from pydantic import BaseModel, Field


class MessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=20000)


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    created_at: str
