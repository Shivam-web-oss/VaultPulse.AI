from datetime import datetime, timezone

from app.services import conversation_service as service_module
from app.services.conversation_service import ConversationService


class Result:
    def __init__(self, one=None, many=None):
        self.one = one
        self.many = many or ([] if one is None else [one])

    def fetchone(self):
        return self.one

    def fetchall(self):
        return self.many


class FakeConnection:
    def __init__(self):
        self.calls = []
        now = datetime.now(timezone.utc)
        self.message = {"id": "message-1", "role": "user", "content": "Find budget laptops", "created_at": now}
        self.conversation = {"id": "conversation-1", "title": "Find budget laptops", "created_at": now, "updated_at": now}

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, sql, params=()):
        self.calls.append((" ".join(sql.split()), params))
        normalized = " ".join(sql.split())
        if normalized.startswith("select id from conversations"):
            return Result({"id": "conversation-1"})
        if normalized.startswith("insert into messages"):
            return Result(self.message)
        if normalized.startswith("select c.id,"):
            return Result(many=[self.conversation])
        return Result()

    def commit(self):
        pass


def test_list_returns_account_scoped_conversations_with_message_titles(monkeypatch):
    fake = FakeConnection()
    monkeypatch.setattr(service_module, "connection", lambda: fake)

    conversations = ConversationService().list("account-a")

    sql, params = fake.calls[0]
    assert "where c.owner_id = %s" in sql
    assert params == ("account-a",)
    assert conversations[0].title == "Find budget laptops"


def test_first_user_message_sets_default_conversation_title(monkeypatch):
    fake = FakeConnection()
    monkeypatch.setattr(service_module, "connection", lambda: fake)

    ConversationService().add_message("conversation-1", "account-a", "user", "Find budget laptops")

    update_sql, update_params = fake.calls[-1]
    assert update_sql.startswith("update conversations c")
    assert "c.title = 'New conversation'" in update_sql
    assert "where c.id = %s and c.owner_id = %s" in update_sql
    assert update_params == ("conversation-1", "account-a")
