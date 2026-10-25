-- Run once if you already applied insert/select RLS and only need DELETE for Preferences UI.
alter table executive_preferences enable row level security;

drop policy if exists "Allow anon delete preferences" on executive_preferences;

create policy "Allow anon delete preferences"
  on executive_preferences for delete
  to anon
  using (true);

grant delete on table executive_preferences to anon;
