-- =====================================================================
-- Search helper functions (vector + trigram) — idempotent & fast
-- =====================================================================
BEGIN;

-- Trigram support for text fallback searches
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Trigram GIN index on content (accelerates % and similarity predicates)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_indexes
    WHERE schemaname='public' AND indexname='documents_content_trgm_idx'
  ) THEN
    CREATE INDEX documents_content_trgm_idx
      ON public.documents
      USING gin (content gin_trgm_ops);
  END IF;
END$$;

-- ---------------------------------------------------------------------
-- KNN by embedding with optional filters and pagination
--   - role filter (exact match)
--   - metadata filter (jsonb containment)
--   - minimum similarity threshold (0..1)
--   - offset/limit (clamped to sane bounds)
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.search_documents_by_embedding(
    emb              vector(1536),
    k                int           DEFAULT 5,
    role_filter      text          DEFAULT NULL,
    metadata_filter  jsonb         DEFAULT NULL,
    min_similarity   double precision DEFAULT NULL,
    row_offset       int           DEFAULT 0
)
RETURNS TABLE(
    id          text,
    content     text,
    metadata    jsonb,
    agent_role  text,
    distance    double precision,
    similarity  double precision,
    created_at  timestamptz
)
LANGUAGE sql
STABLE
AS $$
    SELECT
      d.id,
      d.content,
      d.metadata,
      d.agent_role,
      (d.embedding <=> emb)                                  AS distance,
      GREATEST(0, LEAST(1, 1 - (d.embedding <=> emb)))       AS similarity,
      d.created_at
    FROM public.documents d
    WHERE d.embedding IS NOT NULL
      AND (role_filter     IS NULL OR d.agent_role = role_filter)
      AND (metadata_filter IS NULL OR d.metadata @> metadata_filter)
      AND (min_similarity  IS NULL OR (1 - (d.embedding <=> emb)) >= min_similarity)
    ORDER BY d.embedding <=> emb
    LIMIT LEAST(GREATEST(k, 1), 1000)
    OFFSET GREATEST(row_offset, 0);
$$;

-- ---------------------------------------------------------------------
-- Trigram text search with optional role filter and threshold
--   - Uses % operator to activate trigram index
--   - similarity() for ranking; threshold defaults to 0.1
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.search_documents_by_text(
    query_text     text,
    k              int              DEFAULT 5,
    role_filter    text             DEFAULT NULL,
    min_trgm       double precision DEFAULT 0.10,
    row_offset     int              DEFAULT 0
)
RETURNS TABLE(
    id          text,
    content     text,
    metadata    jsonb,
    agent_role  text,
    similarity  double precision,
    created_at  timestamptz
)
LANGUAGE sql
STABLE
AS $$
    SELECT
      d.id,
      d.content,
      d.metadata,
      d.agent_role,
      similarity(d.content, query_text) AS similarity,
      d.created_at
    FROM public.documents d
    WHERE d.content % query_text
      AND similarity(d.content, query_text) >= min_trgm
      AND (role_filter IS NULL OR d.agent_role = role_filter)
    ORDER BY similarity(d.content, query_text) DESC
    LIMIT LEAST(GREATEST(k, 1), 1000)
    OFFSET GREATEST(row_offset, 0);
$$;

COMMIT;
