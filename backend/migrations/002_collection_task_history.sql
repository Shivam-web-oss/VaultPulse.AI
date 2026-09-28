alter table collection_tasks
    add column if not exists parent_task_id uuid,
    add column if not exists version integer not null default 1;

do $$
begin
    if not exists (
        select 1 from pg_constraint
        where conname = 'collection_tasks_parent_task_id_fkey'
          and conrelid = 'collection_tasks'::regclass
    ) then
        alter table collection_tasks
            add constraint collection_tasks_parent_task_id_fkey
            foreign key (parent_task_id) references collection_tasks(id) on delete set null;
    end if;
end $$;

create index if not exists collection_tasks_parent_task_id_idx
    on collection_tasks(parent_task_id);

create unique index if not exists collection_tasks_parent_version_uidx
    on collection_tasks(parent_task_id, version)
    where parent_task_id is not null;
