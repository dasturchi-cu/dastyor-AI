-- =============================================================================
-- Supabase Storage setup (RUN-READY) — SQL Editor
--
-- Creates a bucket used by the backend upload pipeline.
-- Default bucket name used by code: env SUPABASE_FILES_BUCKET or "files".
--
-- NOTE:
-- - Buckets live in `storage.buckets`.
-- - RLS for Storage is controlled via `storage.objects` policies.
-- - Recommended: keep uploads server-side (service_role) and do NOT allow anon writes.
-- =============================================================================

do $$
declare
  bname text := 'files';
begin
  insert into storage.buckets (id, name, public)
  values (bname, bname, false)
  on conflict (id) do nothing;
end $$;

-- Optional: allow authenticated users to read their own signed URLs only (server-side is still preferred).
-- By default, keep `public=false` and use signed URLs from backend.

