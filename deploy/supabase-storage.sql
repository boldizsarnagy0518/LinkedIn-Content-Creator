-- Use a private schema for Python-owned tables. Do not add it to Supabase's exposed API schemas.
create schema if not exists contentops;
revoke all on schema contentops from public, anon, authenticated;
-- The backend connects using the database owner/session pooler and search_path=contentops.
-- Supabase Auth's public token hook is separate from application storage.
