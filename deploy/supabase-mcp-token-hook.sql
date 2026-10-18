-- Replace BOTH placeholders before running in the Supabase SQL editor.
-- Then enable public.contentops_access_token_hook under Auth > Hooks > Custom Access Token.
-- This changes only tokens issued for the dedicated ContentOps OAuth client.
create or replace function public.contentops_access_token_hook(event jsonb)
returns jsonb
language plpgsql stable
set search_path = ''
as $$
declare
  contentops_client constant text := 'REPLACE_WITH_MCP_OAUTH_CLIENT_ID';
  contentops_resource constant text := 'https://REPLACE_WITH_BACKEND_HOST/mcp';
begin
  if coalesce(event->>'client_id', event->'claims'->>'client_id') = contentops_client then
    return jsonb_set(event, '{claims,aud}', to_jsonb(contentops_resource));
  end if;
  return event;
end;
$$;
grant usage on schema public to supabase_auth_admin;
grant execute on function public.contentops_access_token_hook(jsonb) to supabase_auth_admin;
revoke execute on function public.contentops_access_token_hook(jsonb) from public, anon, authenticated;
