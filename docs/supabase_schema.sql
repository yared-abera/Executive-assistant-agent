-- Run in Supabase SQL Editor (Free Tier + pgvector)
create extension if not exists vector;

create table if not exists executive_preferences (
  id bigserial primary key,
  content text not null,
  embedding vector(768),
  created_at timestamptz default now()
);

create index if not exists executive_preferences_embedding_idx
  on executive_preferences
  using ivfflat (embedding vector_cosine_ops)
  with (lists = 100);

create or replace function match_preferences(
  query_embedding vector(768),
  match_count int default 3
)
returns table (
  id bigint,
  content text,
  similarity float
)
language sql stable
as $$
  select
    p.id,
    p.content,
    1 - (p.embedding <=> query_embedding) as similarity
  from executive_preferences p
  where p.embedding is not null
  order by p.embedding <=> query_embedding
  limit match_count;
$$;

-- Option A: allow the backend anon key to insert/select preferences (demo RLS)
alter table executive_preferences enable row level security;

drop policy if exists "Allow anon insert preferences" on executive_preferences;
drop policy if exists "Allow anon select preferences" on executive_preferences;
drop policy if exists "Allow anon delete preferences" on executive_preferences;

create policy "Allow anon insert preferences"
  on executive_preferences for insert
  to anon
  with check (true);

create policy "Allow anon select preferences"
  on executive_preferences for select
  to anon
  using (true);

create policy "Allow anon delete preferences"
  on executive_preferences for delete
  to anon
  using (true);

grant usage on schema public to anon;
grant select, insert, delete on table executive_preferences to anon;
grant usage, select on sequence executive_preferences_id_seq to anon;
grant execute on function match_preferences(vector, int) to anon;
