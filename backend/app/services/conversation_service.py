import logging
from typing import List, Optional
from uuid import UUID
from uuid import uuid4

from app.db import connection
from app.schemas.conversation import ConversationDetailOut, ConversationOut, MessageOut

logger = logging.getLogger(__name__)


class ConversationService:
    def create(self, owner_id: str, title: str = "New conversation") -> ConversationDetailOut:
        conversation_id = str(uuid4())
        with connection() as conn:
            conn.execute("insert into conversations (id, owner_id, title) values (%s, %s, %s)", (conversation_id, owner_id, title.strip() or "New conversation"))
            conn.commit()
        logger.info("conversation.created conversation_id=%s owner_id=%s", conversation_id, owner_id)
        return self.get_detail(conversation_id, owner_id)  # type: ignore[return-value]

    def list(self, owner_id: str) -> List[ConversationOut]:
        with connection() as conn:
            rows = conn.execute(
                """select c.id,
                          case when c.title = 'New conversation' then coalesce(
                              (select left(trim(regexp_replace(m.content, '[[:space:]]+', ' ', 'g')), 80)
                               from messages m where m.conversation_id = c.id and m.role = 'user'
                               order by m.created_at, m.id limit 1), c.title)
                              else c.title end as title,
                          c.created_at, c.updated_at
                   from conversations c where c.owner_id = %s order by c.updated_at desc""",
                (owner_id,),
            ).fetchall()
        return [ConversationOut(**self._conversation_row(row)) for row in rows]

    def get_detail(self, conversation_id: str, owner_id: str) -> Optional[ConversationDetailOut]:
        with connection() as conn:
            conversation = conn.execute("select id, title, created_at, updated_at from conversations where id = %s and owner_id = %s", (conversation_id, owner_id)).fetchone()
            if conversation is None:
                return None
            messages = conn.execute("select id, role, content, created_at from messages where conversation_id = %s order by created_at", (conversation_id,)).fetchall()
        return ConversationDetailOut(**self._conversation_row(conversation), messages=[MessageOut(**self._message_row(message)) for message in messages])

    @staticmethod
    def _conversation_row(row: dict) -> dict:
        return {**row, "id": str(row["id"]), "created_at": row["created_at"].isoformat(), "updated_at": row["updated_at"].isoformat()}

    @staticmethod
    def _message_row(row: dict) -> dict:
        return {**row, "id": str(row["id"]), "created_at": row["created_at"].isoformat()}

    def add_message(self, conversation_id: str, owner_id: str, role: str, content: str, client_message_id: Optional[UUID] = None) -> MessageOut:
        message_id = str(uuid4())
        with connection() as conn:
            conversation = conn.execute("select id from conversations where id = %s and owner_id = %s", (conversation_id, owner_id)).fetchone()
            if conversation is None:
                raise KeyError(conversation_id)
            if client_message_id is None:
                row = conn.execute("insert into messages (id, conversation_id, role, content) values (%s, %s, %s, %s) returning id, role, content, created_at", (message_id, conversation_id, role, content)).fetchone()
            else:
                row = conn.execute(
                    """insert into messages (id, conversation_id, role, content, client_message_id)
                       values (%s, %s, %s, %s, %s)
                       on conflict (conversation_id, client_message_id, role) where client_message_id is not null
                       do update set content = messages.content
                       returning id, role, content, created_at""",
                    (message_id, conversation_id, role, content, client_message_id),
                ).fetchone()
            conn.execute(
                """update conversations c
                   set title = case when c.title = 'New conversation' then coalesce(
                           (select left(trim(regexp_replace(m.content, '[[:space:]]+', ' ', 'g')), 80)
                            from messages m where m.conversation_id = c.id and m.role = 'user'
                            order by m.created_at, m.id limit 1), c.title)
                       else c.title end,
                       updated_at = now()
                   where c.id = %s and c.owner_id = %s""",
                (conversation_id, owner_id),
            )
            conn.commit()
        logger.info("conversation.message_added conversation_id=%s owner_id=%s role=%s", conversation_id, owner_id, role)
        return MessageOut(**self._message_row(row))

    def rename(self, conversation_id: str, owner_id: str, title: str) -> Optional[ConversationOut]:
        with connection() as conn:
            row = conn.execute("update conversations set title = %s, updated_at = now() where id = %s and owner_id = %s returning id, title, created_at, updated_at", (title.strip(), conversation_id, owner_id)).fetchone()
            conn.commit()
        if row is None:
            return None
        logger.info("conversation.renamed conversation_id=%s owner_id=%s", conversation_id, owner_id)
        return ConversationOut(**self._conversation_row(row))

    def delete(self, conversation_id: str, owner_id: str) -> bool:
        with connection() as conn:
            row = conn.execute("delete from conversations where id = %s and owner_id = %s returning id", (conversation_id, owner_id)).fetchone()
            conn.commit()
        if row is None:
            return False
        logger.info("conversation.deleted conversation_id=%s owner_id=%s", conversation_id, owner_id)
        return True


conversation_service = ConversationService()
