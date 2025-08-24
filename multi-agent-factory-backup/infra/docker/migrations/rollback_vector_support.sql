-- =====================================================================
-- Rollback for pgvector RAG + agent results schema
-- =====================================================================
BEGIN;

-- Drop vector indexes (both variants, whichever exists)
DROP INDEX IF EXISTS public.documents_embedding_hnsw_cos_idx;
DROP INDEX IF EXISTS public.documents_embedding_cos_idx;

-- Drop helpers
DROP INDEX IF EXISTS public.documents_created_at_desc_idx;
DROP INDEX IF EXISTS public.documents_agent_role_created_at_idx;  -- if you added it later
DROP INDEX IF EXISTS public.documents_agent_role_idx;
DROP INDEX IF EXISTS public.results_status_created_idx;
DROP INDEX IF EXISTS public.results_role_idx;
DROP INDEX IF EXISTS public.results_metadata_gin_idx;
DROP INDEX IF EXISTS public.documents_metadata_gin_idx;

-- Triggers & function
DROP TRIGGER IF EXISTS results_set_updated_at ON public.results;
DROP TRIGGER IF EXISTS documents_set_updated_at ON public.documents;
DROP FUNCTION IF EXISTS public.set_updated_at();

-- Tables
DROP TABLE IF EXISTS public.results;
DROP TABLE IF EXISTS public.documents;

-- Extension intentionally kept (other schemas may use it)
-- DROP EXTENSION IF EXISTS vector;

COMMIT;
