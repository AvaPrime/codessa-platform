-- =====================================================================
-- pgvector RAG + agent results schema (idempotent, production-hardened)
-- =====================================================================
BEGIN;

-- 1) Ensure pgvector is available
CREATE EXTENSION IF NOT EXISTS vector;

-- 2) Tables
CREATE TABLE IF NOT EXISTS public.documents (
    id          TEXT PRIMARY KEY,
    content     TEXT NOT NULL,
    embedding   vector(1536),                        -- nullable: allow staged ingest
    metadata    JSONB NOT NULL DEFAULT '{}'::jsonb,
    agent_role  TEXT,
    created_at  timestamptz NOT NULL DEFAULT (now() AT TIME ZONE 'utc'),
    updated_at  timestamptz NOT NULL DEFAULT (now() AT TIME ZONE 'utc'),
    -- keep content non-empty (whitespace-only rejected)
    CONSTRAINT documents_content_not_blank CHECK (length(btrim(content)) > 0)
);

CREATE TABLE IF NOT EXISTS public.results (
    task_id     TEXT PRIMARY KEY,
    role        TEXT NOT NULL,
    content     TEXT NOT NULL,
    metadata    JSONB NOT NULL DEFAULT '{}'::jsonb,
    status      TEXT NOT NULL DEFAULT 'completed',
    created_at  timestamptz NOT NULL DEFAULT (now() AT TIME ZONE 'utc'),
    updated_at  timestamptz NOT NULL DEFAULT (now() AT TIME ZONE 'utc'),
    CONSTRAINT results_status_chk CHECK (status IN ('queued','running','completed','failed'))
);

-- 3) updated_at trigger (shared)
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.updated_at := (now() AT TIME ZONE 'utc');
  RETURN NEW;
END;
$$;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'documents_set_updated_at') THEN
    CREATE TRIGGER documents_set_updated_at
      BEFORE UPDATE ON public.documents
      FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'results_set_updated_at') THEN
    CREATE TRIGGER results_set_updated_at
      BEFORE UPDATE ON public.results
      FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
  END IF;
END$$;

-- 4) Indexes
-- 4a) Metadata GIN (jsonb)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_indexes WHERE schemaname='public' AND indexname='documents_metadata_gin_idx'
  ) THEN
    CREATE INDEX documents_metadata_gin_idx
      ON public.documents USING gin (metadata);
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_indexes WHERE schemaname='public' AND indexname='results_metadata_gin_idx'
  ) THEN
    CREATE INDEX results_metadata_gin_idx
      ON public.results USING gin (metadata);
  END IF;
END$$;

-- 4b) Helper B-tree indexes for common filters
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_indexes WHERE schemaname='public' AND indexname='results_role_idx'
  ) THEN
    CREATE INDEX results_role_idx ON public.results (role);
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_indexes WHERE schemaname='public' AND indexname='documents_agent_role_idx'
  ) THEN
    CREATE INDEX documents_agent_role_idx ON public.documents (agent_role);
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_indexes WHERE schemaname='public' AND indexname='documents_created_at_desc_idx'
  ) THEN
    CREATE INDEX documents_created_at_desc_idx ON public.documents (created_at DESC);
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_indexes WHERE schemaname='public' AND indexname='results_status_created_idx'
  ) THEN
    CREATE INDEX results_status_created_idx ON public.results (status, created_at DESC);
  END IF;

END$$;

-- 4c) Vector ANN index:
--     Prefer HNSW if pgvector >= 0.5.0; otherwise fall back to IVFFLAT(lists=100).
--     Make it PARTIAL to skip rows where embedding IS NULL.
DO $$
DECLARE
  v_major int := 0;
  v_minor int := 0;
  v_patch int := 0;
  v_num   int := 0;
BEGIN
  SELECT
    COALESCE(split_part(extversion,'.',1),'0')::int,
    COALESCE(split_part(extversion,'.',2),'0')::int,
    COALESCE(NULLIF(split_part(extversion,'.',3),''),'0')::int
  INTO v_major, v_minor, v_patch
  FROM pg_extension WHERE extname = 'vector';

  v_num := (v_major*10000 + v_minor*100 + v_patch);

  -- If HNSW-capable and index not present, create HNSW
  IF v_num >= 500 THEN
    IF NOT EXISTS (
      SELECT 1 FROM pg_indexes WHERE schemaname='public' AND indexname='documents_embedding_hnsw_cos_idx'
    ) THEN
      CREATE INDEX documents_embedding_hnsw_cos_idx
        ON public.documents
        USING hnsw (embedding vector_cosine_ops)
        WHERE embedding IS NOT NULL;
    END IF;
  ELSE
    -- Fallback: IVFFLAT
    IF NOT EXISTS (
      SELECT 1 FROM pg_indexes WHERE schemaname='public' AND indexname='documents_embedding_cos_idx'
    ) THEN
      CREATE INDEX documents_embedding_cos_idx
        ON public.documents
        USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)
        WHERE embedding IS NOT NULL;
    END IF;
  END IF;
END$$;

-- Fresh stats help ANN planners
ANALYZE public.documents;

COMMIT;
