CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    embedding VECTOR(1536),
    metadata JSONB
);

CREATE TABLE IF NOT EXISTS results (
    task_id   TEXT PRIMARY KEY,
    role      TEXT NOT NULL,
    content   TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Vector index for cosine search
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes WHERE schemaname = 'public' AND indexname = 'documents_embedding_cos_idx'
    ) THEN
        CREATE INDEX documents_embedding_cos_idx ON documents
        USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
    END IF;
END$$;

-- Results ordering index
CREATE INDEX IF NOT EXISTS results_created_at_idx ON results (created_at DESC);

-- Helpful after index creation
ANALYZE documents;
ANALYZE results;

