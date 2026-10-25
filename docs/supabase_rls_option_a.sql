-- Fix: RLS blocking preference inserts with the anon key.
-- Run once in Supabase Dashboard → SQL Editor → New query → Run
-- (Safe if you already created executive_preferences from supabase_schema.sql)

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
