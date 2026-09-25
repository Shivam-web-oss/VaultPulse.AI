from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import uuid4

from app.schemas.conversation import ConversationDetailOut, ConversationOut, MessageOut


class ConversationService:
    def __init__(self) -> None:
        self._conversations: Dict[str, dict] = {}

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def create(self, owner_id: str, title: str = "New conversation") -> ConversationDetailOut:
        conversation_id = str(uuid4())
        now = self._now()
        self._conversations[conversation_id] = {
            "id": conversation_id,
            "owner_id": owner_id,
            "title": title.strip() or "New conversation",
            "created_at": now,
            "updated_at": now,
            "messages": [],
        }
        return self.get_detail(conversation_id, owner_id)  # type: ignore[return-value]

    def list(self, owner_id: str) -> List[ConversationOut]:
        return [ConversationOut(**conversation) for conversation in self._conversations.values() if conversation["owner_id"] == owner_id]

    def get_detail(self, conversation_id: str, owner_id: str) -> Optional[ConversationDetailOut]:
        conversation = self._conversations.get(conversation_id)
        if conversation is None or conversation["owner_id"] != owner_id:
            return None
        return ConversationDetailOut(**conversation)

    def add_message(self, conversation_id: str, owner_id: str, role: str, content: str) -> MessageOut:
        conversation = self._conversations.get(conversation_id)
        if conversation is None or conversation["owner_id"] != owner_id:
            raise KeyError(conversation_id)

        message = {
            "id": str(uuid4()),
            "role": role,
            "content": content,
            "created_at": self._now(),
        }
        conversation["messages"].append(message)
        conversation["updated_at"] = message["created_at"]
        return MessageOut(**message)

    def rename(self, conversation_id: str, owner_id: str, title: str) -> Optional[ConversationOut]:
        conversation = self._conversations.get(conversation_id)
        if conversation is None or conversation["owner_id"] != owner_id:
            return None
        conversation["title"] = title.strip()
        conversation["updated_at"] = self._now()
        return ConversationOut(**conversation)

    def delete(self, conversation_id: str, owner_id: str) -> bool:
        conversation = self._conversations.get(conversation_id)
        if conversation is None or conversation["owner_id"] != owner_id:
            return False
        self._conversations.pop(conversation_id)
        return True


conversation_service = ConversationService()
