alter table messages
    add column if not exists client_message_id uuid;

create unique index if not exists messages_client_request_role_unique
    on messages (conversation_id, client_message_id, role)
    where client_message_id is not null;
