create table if not exists app_users (
    id uuid primary key,
    name text not null check (char_length(trim(name)) >= 2),
    email text not null unique check (email = lower(email)),
    salt text not null,
    password_hash text not null,
    created_at timestamptz not null default now()
);

create table if not exists auth_sessions (
    token text primary key,
    user_id uuid not null references app_users(id) on delete cascade,
    created_at timestamptz not null default now()
);

create table if not exists conversations (
    id uuid primary key,
    owner_id uuid not null references app_users(id) on delete cascade,
    title text not null check (char_length(trim(title)) between 1 and 120),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);
create index if not exists conversations_owner_updated_idx on conversations(owner_id, updated_at desc);

create table if not exists messages (
    id uuid primary key,
    conversation_id uuid not null references conversations(id) on delete cascade,
    role text not null check (role in ('user', 'assistant')),
    content text not null check (char_length(trim(content)) > 0),
    created_at timestamptz not null default now()
);
create index if not exists messages_conversation_created_idx on messages(conversation_id, created_at);

create table if not exists documents (
    id uuid primary key,
    owner_id uuid not null references app_users(id) on delete cascade,
    name text not null,
    content_type text not null,
    size integer not null check (size >= 0),
    text_content text not null default '',
    created_at timestamptz not null default now()
);
create index if not exists documents_owner_idx on documents(owner_id);

create table if not exists collection_tasks (
    id uuid primary key,
    owner_id uuid not null references app_users(id) on delete cascade,
    prompt text not null check (char_length(trim(prompt)) > 0),
    status text not null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    dataset jsonb not null default '{}'::jsonb,
    cancel_requested boolean not null default false
);
create index if not exists collection_tasks_owner_updated_idx on collection_tasks(owner_id, updated_at desc);

create table if not exists collection_events (
    id bigint generated always as identity primary key,
    task_id uuid not null references collection_tasks(id) on delete cascade,
    event text not null,
    data jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);
create index if not exists collection_events_task_id_idx on collection_events(task_id, id);
