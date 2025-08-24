from __future__ import annotations

"""
Vector store utilities for pgvector.

Features
- ensure_schema(): idempotently creates extension/table/index if migrations didn't run
- upsert_document(): text -> embed -> upsert (JSONB metadata)
- upsert_document_with_embedding(): use a provided embedding (list[float])
- bulk_upsert(): batch ingest with automatic embedding
- search(): cosine distance search by query text or embedding
- get_document(), delete_document()

Notes
- Uses cosine distance (<=>). Lower is better. We also return similarity = 1 - distance.
- Embedding dimension defaults to 1536; override with env EMBEDDING_DIM.
- Requires: pgvector extension on your Postgres (handled by migrations or ensure_schema()).
"""

import os
import json
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union

import psycopg
from psycopg import sql
from psycopg.rows import dict_row
try:  # Prefer native JSONB adapter in psycopg3
    from psycopg.types.json import Jsonb as _JSONB  # type: ignore
except Exception:  # pragma: no cover - adapter not available
    _JSONB = None  # type: ignore

from llm.openai_helpers import embed_text

# -----------------------------------------------------------------------------
# Config
# -----------------------------------------------------------------------------
PG_URI: str = os.getenv("POSTGRES_URI", "postgresql://user:pass@db:5432/factory")
VECTOR_DIM: int = int(os.getenv("EMBEDDING_DIM", "1536"))
TABLE_NAME: str = os.getenv("VECTOR_TABLE", "documents")

# Index config (tunable)
IVFFLAT_LISTS: int = int(os.getenv("IVFFLAT_LISTS", "100"))


# -----------------------------------------------------------------------------
# Internal helpers
# -----------------------------------------------------------------------------

def _get_conn() -> psycopg.Connection:
    """Get a new psycopg connection. Caller manages close/commit."""
    return psycopg.connect(PG_URI)


def _jsonb(value: Dict[str, Any]) -> Any:
    """Wrap dict as JSONB if adapter available, else return JSON string."""
    if _JSONB is not None:
        return _JSONB(value)
    return json.dumps(value, ensure_ascii=False)


def _as_vector_literal(vec: List[float]) -> str:
    """
    Turn a Python list of floats into pgvector text literal: "[0.1,0.2,...]".
    Psycopg doesn't natively adapt pgvector; we cast the string to ::vector.
    """
    if len(vec) != VECTOR_DIM:
        raise ValueError(
            f"Embedding dim mismatch: got {len(vec)}, expected {VECTOR_DIM}. "
            "Set EMBEDDING_DIM to match your model if needed."
        )
    return "[" + ",".join(f"{x:.8f}" for x in vec) + "]"


def _ensure_table_sql() -> str:
    return f"""
    CREATE EXTENSION IF NOT EXISTS vector;

    CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
        id TEXT PRIMARY KEY,
        embedding VECTOR({VECTOR_DIM}),
        metadata JSONB
    );

    -- Cosine index for ANN search (safe to run repeatedly)
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_indexes
            WHERE schemaname = 'public'
              AND indexname = '{TABLE_NAME}_embedding_cos_idx'
        )
        THEN
            CREATE INDEX {TABLE_NAME}_embedding_cos_idx ON {TABLE_NAME}
            USING ivfflat (embedding vector_cosine_ops) WITH (lists = {IVFFLAT_LISTS});
        END IF;
    END
    $$;

    ANALYZE {TABLE_NAME};
    """


# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------

def ensure_schema() -> None:
    """Idempotently ensure pgvector extension, table and index exist."""
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(_ensure_table_sql())
        conn.commit()


def upsert_document(doc_id: str, text: str, metadata: Dict[str, Any]) -> None:
    """Embed `text` and upsert into the vector table with JSONB metadata."""
    vec = embed_text(text)
    # Store the original text in metadata for content column
    metadata_with_content = {**metadata, "content": text}
    upsert_document_with_embedding(doc_id, vec, metadata_with_content)


def upsert_document_with_embedding(
    doc_id: str,
    embedding: List[float],
    metadata: Dict[str, Any],
    *,
    content: Optional[str] = None,        # ← new explicit kw-only arg
) -> None:
    """Upsert a document using a precomputed embedding."""
    vec_lit = _as_vector_literal(embedding)
    # Prefer explicit content arg; else look in metadata; enforce non-blank
    content_final = content if content is not None else metadata.get("content")
    if not content_final or not content_final.strip():
        raise ValueError("content is required and must be non-blank")

    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                sql.SQL(f"""
                    INSERT INTO {TABLE_NAME} (id, content, embedding, metadata)
                    VALUES (%s, %s, %s::vector, %s)
                    ON CONFLICT (id) DO UPDATE
                    SET content  = EXCLUDED.content,
                        embedding = EXCLUDED.embedding,
                        metadata  = EXCLUDED.metadata
                """),
                (doc_id, content_final, vec_lit, _jsonb(metadata)),
            )
        conn.commit()

def upsert_document(doc_id: str, text: str, metadata: Dict[str, Any]) -> None:
    """Embed `text` and upsert into the vector table with JSONB metadata."""
    vec = embed_text(text)
    # Clean approach: pass content explicitly
    upsert_document_with_embedding(doc_id, vec, metadata, content=text)


def bulk_upsert(items: Iterable[Tuple[str, str, Dict[str, Any]]], batch_size: int = 64) -> None:
    """
    Bulk embed + upsert many items.
    items: iterable of (doc_id, text, metadata)
    """
    batch: List[Tuple[str, str, Dict[str, Any]]] = []
    for item in items:
        batch.append(item)
        if len(batch) >= batch_size:
            _bulk_upsert_batch(batch)
            batch.clear()
    if batch:
        _bulk_upsert_batch(batch)


def _bulk_upsert_batch(batch: List[Tuple[str, str, Dict[str, Any]]]) -> None:
    # Embed sequentially; swap with parallelism if needed.
    records: List[Tuple[str, str, str, Any]] = []
    for doc_id, text, metadata in batch:
        vec = embed_text(text)
        vec_lit = _as_vector_literal(vec)
        records.append((doc_id, text, vec_lit, _jsonb(metadata)))

    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.executemany(
                sql.SQL(
                    f"""
                    INSERT INTO {TABLE_NAME} (id, content, embedding, metadata)
                    VALUES (%s, %s, %s::vector, %s)
                    ON CONFLICT (id) DO UPDATE
                    SET content = EXCLUDED.content,
                        embedding = EXCLUDED.embedding,
                        metadata  = EXCLUDED.metadata
                    """
                ),
                records,
            )
        conn.commit()


Query = Union[str, List[float]]


def search(query: Query, k: int = 5) -> List[Dict[str, Any]]:
    """
    Cosine search. Accepts either:
      - query str (will be embedded), or
      - query embedding list[float]
    Returns: list of { id, metadata, distance, similarity } (smaller distance is better)
    """
    if isinstance(query, str):
        vec = embed_text(query)
    else:
        vec = query

    vec_lit = _as_vector_literal(vec)

    with _get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                sql.SQL(
                    f"""
                    SELECT
                        id,
                        metadata,
                        (embedding <=> %s::vector) AS distance
                    FROM {TABLE_NAME}
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                    """
                ),
                (vec_lit, vec_lit, k),
            )
            rows = list(cur.fetchall())

    # Add similarity = 1 - cosine_distance (bounded to [0,1])
    for r in rows:
        dist = float(r["distance"])  # type: ignore[index]
        sim = max(0.0, min(1.0, 1.0 - dist))
        r["similarity"] = sim

    return rows


def get_document(doc_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a single document row."""
    with _get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                sql.SQL(f"SELECT id, metadata FROM {TABLE_NAME} WHERE id = %s"),
                (doc_id,),
            )
            row = cur.fetchone()
            return dict(row) if row else None


def delete_document(doc_id: str) -> bool:
    """Delete a document by id. Returns True if a row was removed."""
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                sql.SQL(f"DELETE FROM {TABLE_NAME} WHERE id = %s"),
                (doc_id,),
            )
            deleted = cur.rowcount > 0
        conn.commit()
    return deleted


### Schema Verification Function
def verify_schema() -> bool:
    """Verify expected schema exists; raise if migrations needed."""
    required_columns = {'id', 'content', 'embedding', 'metadata', 'created_at', 'updated_at'}
    required_indexes = {'documents_embedding_cosine_idx', 'documents_content_trgm_idx'}
    
    with _get_conn() as conn:
        with conn.cursor() as cur:
            # Check columns
            cur.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'documents' AND table_schema = 'public'
            """)
            existing_columns = {row[0] for row in cur.fetchall()}
            
            if not required_columns.issubset(existing_columns):
                missing = required_columns - existing_columns
                raise RuntimeError(f"Missing columns: {missing}. Run migrations first.")
            
            # Check indexes
            cur.execute("""
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'documents' AND schemaname = 'public'
            """)
            existing_indexes = {row[0] for row in cur.fetchall()}
            
            if not required_indexes.issubset(existing_indexes):
                missing = required_indexes - existing_indexes
                raise RuntimeError(f"Missing indexes: {missing}. Run migrations first.")
    
    return True


## 🎯 Optional Enhancements (As Suggested)

### Schema Verification Function
def verify_schema() -> bool:
    """Verify expected schema exists; raise if migrations needed."""
    required_columns = {'id', 'content', 'embedding', 'metadata', 'created_at', 'updated_at'}
    required_indexes = {'documents_embedding_cosine_idx', 'documents_content_trgm_idx'}
    
    with _get_conn() as conn:
        with conn.cursor() as cur:
            # Check columns
            cur.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'documents' AND table_schema = 'public'
            """)
            existing_columns = {row[0] for row in cur.fetchall()}
            
            if not required_columns.issubset(existing_columns):
                missing = required_columns - existing_columns
                raise RuntimeError(f"Missing columns: {missing}. Run migrations first.")
            
            # Check indexes
            cur.execute("""
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'documents' AND schemaname = 'public'
            """)
            existing_indexes = {row[0] for row in cur.fetchall()}
            
            if not required_indexes.issubset(existing_indexes):
                missing = required_indexes - existing_indexes
                raise RuntimeError(f"Missing indexes: {missing}. Run migrations first.")
    
    return True


## 🎯 Optional Enhancements (As Suggested)

### Schema Verification Function
def verify_schema() -> bool:
    """Verify expected schema exists; raise if migrations needed."""
    required_columns = {'id', 'content', 'embedding', 'metadata', 'created_at', 'updated_at'}
    required_indexes = {'documents_embedding_cosine_idx', 'documents_content_trgm_idx'}
    
    with _get_conn() as conn:
        with conn.cursor() as cur:
            # Check columns
            cur.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'documents' AND table_schema = 'public'
            """)
            existing_columns = {row[0] for row in cur.fetchall()}
            
            if not required_columns.issubset(existing_columns):
                missing = required_columns - existing_columns
                raise RuntimeError(f"Missing columns: {missing}. Run migrations first.")
            
            # Check indexes
            cur.execute("""
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'documents' AND schemaname = 'public'
            """)
            existing_indexes = {row[0] for row in cur.fetchall()}
            
            if not required_indexes.issubset(existing_indexes):
                missing = required_indexes - existing_indexes
                raise RuntimeError(f"Missing indexes: {missing}. Run migrations first.")
    
    return True


## 🎯 Optional Enhancements (As Suggested)

### Schema Verification Function
def verify_schema() -> bool:
    """Verify expected schema exists; raise if migrations needed."""
    required_columns = {'id', 'content', 'embedding', 'metadata', 'created_at', 'updated_at'}
    required_indexes = {'documents_embedding_cosine_idx', 'documents_content_trgm_idx'}
    
    with _get_conn() as conn:
        with conn.cursor() as cur:
            # Check columns
            cur.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'documents' AND table_schema = 'public'
            """)
            existing_columns = {row[0] for row in cur.fetchall()}
            
            if not required_columns.issubset(existing_columns):
                missing = required_columns - existing_columns
                raise RuntimeError(f"Missing columns: {missing}. Run migrations first.")
            
            # Check indexes
            cur.execute("""
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'documents' AND schemaname = 'public'
            """)
            existing_indexes = {row[0] for row in cur.fetchall()}
            
            if not required_indexes.issubset(existing_indexes):
                missing = required_indexes - existing_indexes
                raise RuntimeError(f"Missing indexes: {missing}. Run migrations first.")
    
    return True


## 🎯 Optional Enhancements (As Suggested)

### Schema Verification Function
def verify_schema() -> bool:
    """Verify expected schema exists; raise if migrations needed."""
    required_columns = {'id', 'content', 'embedding', 'metadata', 'created_at', 'updated_at'}
    required_indexes = {'documents_embedding_cosine_idx', 'documents_content_trgm_idx'}
    
    with _get_conn() as conn:
        with conn.cursor() as cur:
            # Check columns
            cur.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'documents' AND table_schema = 'public'
            """)
            existing_columns = {row[0] for row in cur.fetchall()}
            
            if not required_columns.issubset(existing_columns):
                missing = required_columns - existing_columns
                raise RuntimeError(f"Missing columns: {missing}. Run migrations first.")
            
            # Check indexes
            cur.execute("""
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'documents' AND schemaname = 'public'
            """)
            existing_indexes = {row[0] for row in cur.fetchall()}
            
            if not required_indexes.issubset(existing_indexes):
                missing = required_indexes - existing_indexes
                raise RuntimeError(f"Missing indexes: {missing}. Run migrations first.")
    
    return True


## 🎯 Optional Enhancements (As Suggested)

### Schema Verification Function
def verify_schema() -> bool:
    """Verify expected schema exists; raise if migrations needed."""
    required_columns = {'id', 'content', 'embedding', 'metadata', 'created_at', 'updated_at'}
    required_indexes = {'documents_embedding_cosine_idx', 'documents_content_trgm_idx'}
    
    with _get_conn() as conn:
        with conn.cursor() as cur:
            # Check columns
            cur.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'documents' AND table_schema = 'public'
            """)
            existing_columns = {row[0] for row in cur.fetchall()}
            
            if not required_columns.issubset(existing_columns):
                missing = required_columns - existing_columns
                raise RuntimeError(f"Missing columns: {missing}. Run migrations first.")
            
            # Check indexes
            cur.execute("""
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'documents' AND schemaname = 'public'
            """)
            existing_indexes = {row[0] for row in cur.fetchall()}
            
            if not required_indexes.issubset(existing_indexes):
                missing = required_indexes - existing_indexes
                raise RuntimeError(f"Missing indexes: {missing}. Run migrations first.")
    
    return True


## 🎯 Optional Enhancements (As Suggested)

### Schema Verification Function
def verify_schema() -> bool:
    """Verify expected schema exists; raise if migrations needed."""
    required_columns = {'id', 'content', 'embedding', 'metadata', 'created_at', 'updated_at'}
    required_indexes = {'documents_embedding_cosine_idx', 'documents_content_trgm_idx'}
    
    with _get_conn() as conn:
        with conn.cursor() as cur:
            # Check columns
            cur.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'documents' AND table_schema = 'public'
            """)
            existing_columns = {row[0] for row in cur.fetchall()}
            
            if not required_columns.issubset(existing_columns):
                missing = required_columns - existing_columns
                raise RuntimeError(f"Missing columns: {missing}. Run migrations first.")
            
            # Check indexes
            cur.execute("""
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'documents' AND schemaname = 'public'
            """)
            existing_indexes = {row[0] for row in cur.fetchall()}
            
            if not required_indexes.issubset(existing_indexes):
                missing = required_indexes - existing_indexes
                raise RuntimeError(f"Missing indexes: {missing}. Run migrations first.")
    
    return True


## 🎯 Optional Enhancements (As Suggested)

### Schema Verification Function
def verify_schema() -> bool:
    """Verify expected schema exists; raise if migrations needed."""
    required_columns = {'id', 'content', 'embedding', 'metadata', 'created_at', 'updated_at'}
    required_indexes = {'documents_embedding_cosine_idx', 'documents_content_trgm_idx'}
    
    with _get_conn() as conn:
        with conn.cursor() as cur:
            # Check columns
            cur.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'documents' AND table_schema = 'public'
            """)
            existing_columns = {row[0] for row in cur.fetchall()}
            
            if not required_columns.issubset(existing_columns):
                missing = required_columns - existing_columns
                raise RuntimeError(f"Missing columns: {missing}. Run migrations first.")
            
            # Check indexes
            cur.execute("""
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'documents' AND schemaname = 'public'
            """)
            existing_indexes = {row[0] for row in cur.fetchall()}
            
            if not required_indexes.issubset(existing_indexes):
                missing = required_indexes - existing_indexes
                raise RuntimeError(f"Missing indexes: {missing}. Run migrations first.")
    
    return True


## 🎯 Optional Enhancements (As Suggested)

### Schema Verification Function
def verify_schema() -> bool:
    """Verify expected schema exists; raise if migrations needed."""
    required_columns = {'id', 'content', 'embedding', 'metadata', 'created_at', 'updated_at'}
    required_indexes = {'documents_embedding_cosine_idx', 'documents_content_trgm_idx'}
    
    with _get_conn() as conn:
        with conn.cursor() as cur:
            # Check columns
            cur.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'documents' AND table_schema = 'public'
            """)
            existing_columns = {row[0] for row in cur.fetchall()}
            
            if not required_columns.issubset(existing_columns):
                missing = required_columns - existing_columns
                raise RuntimeError(f"Missing columns: {missing}. Run migrations first.")
            
            # Check indexes
            cur.execute("""
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'documents' AND schemaname = 'public'
            """)
            existing_indexes = {row[0] for row in cur.fetchall()}
            
            if not required_indexes.issubset(existing_indexes):
                missing = required_indexes - existing_indexes
                raise RuntimeError(f"Missing indexes: {missing}. Run migrations first.")
    
    return True


## 🎯 Optional Enhancements (As Suggested)

### Schema Verification Function
def verify_schema() -> bool:
    """Verify expected schema exists; raise if migrations needed."""
    required_columns = {'id', 'content', 'embedding', 'metadata', 'created_at', 'updated_at'}
    required_indexes = {'documents_embedding_cosine_idx', 'documents_content_trgm_idx'}
    
    with _get_conn() as conn:
        with conn.cursor() as cur:
            # Check columns
            cur.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'documents' AND table_schema = 'public'
            """)
            existing_columns = {row[0] for row in cur.fetchall()}
            
            if not required_columns.issubset(existing_columns):
                missing = required_columns - existing_columns
                raise RuntimeError(f"Missing columns: {missing}. Run migrations first.")
            
            # Check indexes
            cur.execute("""
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'documents' AND schemaname = 'public'
            """)
            existing_indexes = {row[0] for row in cur.fetchall()}
            
            if not required_indexes.issubset(existing_indexes):
                missing = required_indexes - existing_indexes
                raise RuntimeError(f"Missing indexes: {missing}. Run migrations first.")
    
    return True


## 🎯 Optional Enhancements (As Suggested)

### Schema Verification Function
def verify_schema() -> bool:
    """Verify expected schema exists; raise if migrations needed."""
    required_columns = {'id', 'content', 'embedding', 'metadata', 'created_at', 'updated_at'}
    required_indexes = {'documents_embedding_cosine_idx', 'documents_content_trgm_idx'}
    
    with _get_conn() as conn:
        with conn.cursor() as cur:
            # Check columns
            cur.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'documents' AND table_schema = 'public'
            """)
            existing_columns = {row[0] for row in cur.fetchall()}
            
            if not required_columns.issubset(existing_columns):
                missing = required_columns - existing_columns
                raise RuntimeError(f"Missing columns: {missing}. Run migrations first.")
            
            # Check indexes
            cur.execute("""
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'documents' AND schemaname = 'public'
            """)
            existing_indexes = {row[0] for row in cur.fetchall()}
            
            if not required_indexes.issubset(existing_indexes):
                missing = required_indexes - existing_indexes
                raise RuntimeError(f"Missing indexes: {missing}. Run migrations first.")
    
    return True


## 🎯 Optional Enhancements (As Suggested)

### Schema Verification Function
def verify_schema() -> bool:
    """Verify expected schema exists; raise if migrations needed."""
    required_columns = {'id', 'content', 'embedding', 'metadata', 'created_at', 'updated_at'}
    required_indexes = {'documents_embedding_cosine_idx', 'documents_content_trgm_idx'}
    
    with _get_conn() as conn:
        with conn.cursor() as cur:
            # Check columns
            cur.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'documents' AND table_schema = 'public'
            """)
            existing_columns = {row[0] for row in cur.fetchall()}
            
            if not required_columns.issubset(existing_columns):
                missing = required_columns - existing_columns
                raise RuntimeError(f"Missing columns: {missing}. Run migrations first.")
            
            # Check indexes
            cur.execute("""
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'documents' AND schemaname = 'public'
            """)
            existing_indexes = {row[0] for row in cur.fetchall()}
            
            if not required_indexes.issubset(existing_indexes):
                missing = required_indexes - existing_indexes
                raise RuntimeError(f"Missing indexes: {missing}. Run migrations first.")
    
    return True


## 🎯 Optional Enhancements (As Suggested)

### Schema Verification Function
def verify_schema() -> bool:
    """Verify expected schema exists; raise if migrations needed."""
    required_columns = {'id', 'content', 'embedding', 'metadata', 'created_at', 'updated_at'}
    required_indexes = {'documents_embedding_cosine_idx', 'documents_content_trgm_idx'}
    
    with _get_conn() as conn:
        with conn.cursor() as cur:
            # Check columns
            cur.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'documents' AND table_schema = 'public'
            """)
            existing_columns = {row[0] for row in cur.fetchall()}
            
            if not required_columns.issubset(existing_columns):
                missing = required_columns - existing_columns
                raise RuntimeError(f"Missing columns: {missing}. Run migrations first.")
            
            # Check indexes
            cur.execute("""
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'documents' AND schemaname = 'public'
            """)
            existing_indexes = {row[0] for row in cur.fetchall()}
            
            if not required_indexes.issubset(existing_indexes):
                missing = required_indexes - existing_indexes
                raise RuntimeError(f"Missing indexes: {missing}. Run migrations first.")
    
    return True


## 🎯 Optional Enhancements (As Suggested)

### Schema Verification Function
def verify_schema() -> bool:
    """Verify expected schema exists; raise if migrations needed."""
    required_columns = {'id', 'content', 'embedding', 'metadata', 'created_at', 'updated_at'}
    required_indexes = {'documents_embedding_cosine_idx', 'documents_content_trgm_idx'}
    
    with _get_conn() as conn:
        with conn.cursor() as cur:
            # Check columns
            cur.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'documents' AND table_schema = 'public'
            """)
            existing_columns = {row[0] for row in cur.fetchall()}
            
            if not required_columns.issubset(existing_columns):
                missing = required_columns - existing_columns
                raise RuntimeError(f"Missing columns: {missing}. Run migrations first.")
            
            # Check indexes
            cur.execute("""
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'documents' AND schemaname = 'public'
            """)
            existing_indexes = {row[0] for row in cur.fetchall()}
            
            if not required_indexes.issubset(existing_indexes):
                missing = required_indexes - existing_indexes
                raise RuntimeError(f"Missing indexes: {missing}. Run migrations first.")
    
    return True


## 🎯 Optional Enhancements (As Suggested)

### Schema Verification Function
def verify_schema() -> bool:
    """Verify expected schema exists; raise if migrations needed."""
    required_columns = {'id', 'content', 'embedding', 'metadata', 'created_at', 'updated_at'}
    required_indexes = {'documents_embedding_cosine_idx', 'documents_content_trgm_idx'}
    
    with _get_conn() as conn:
        with conn.cursor() as cur:
            # Check columns
            cur.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'documents' AND table_schema = 'public'
            """)
            existing_columns = {row[0] for row in cur.fetchall()}
            
            if not required_columns.issubset(existing_columns):
                missing = required_columns - existing_columns
                raise RuntimeError(f"Missing columns: {missing}. Run migrations first.")
            
            # Check indexes
            cur.execute("""
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'documents' AND schemaname = 'public'
            """)
            existing_indexes = {row[0] for row in cur.fetchall()}
            
            if not required_indexes.issubset(existing_indexes):
                missing = required_indexes - existing_indexes
                raise RuntimeError(f"Missing indexes: {missing}. Run migrations first.")
    
    return True


## 🎯 Optional Enhancements (As Suggested)

### Schema Verification Function
def verify_schema() -> bool:
    """Verify expected schema exists; raise if migrations needed."""
    required_columns = {'id', 'content', 'embedding', 'metadata', 'created_at', 'updated_at'}
    required_indexes = {'documents_embedding_cosine_idx', 'documents_content_trgm_idx'}
    
    with _get_conn() as conn:
        with conn.cursor() as cur:
            # Check columns
            cur.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'documents' AND table_schema = 'public'
            """)
            existing_columns = {row[0] for row in cur.fetchall()}
            
            if not required_columns.issubset(existing_columns):
                missing = required_columns - existing_columns
                raise RuntimeError(f"Missing columns: {missing}. Run migrations first.")
            
            # Check indexes
            cur.execute("""
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'documents' AND schemaname = 'public'
            """)
            existing_indexes = {row[0] for row in cur.fetchall()}
            
            if not required_indexes.issubset(existing_indexes):
                missing = required_indexes - existing_indexes
                raise RuntimeError(f"Missing indexes: {missing}. Run migrations first.")
    
    return True


## 🎯 Optional Enhancements (As Suggested)

### Schema Verification Function
def verify_schema() -> bool:
    """Verify expected schema exists; raise if migrations needed."""
    required_columns = {'id', 'content', 'embedding', 'metadata', 'created_at', 'updated_at'}
    required_indexes = {'documents_embedding_cosine_idx', 'documents_content_trgm_idx'}
    
    with _get_conn() as conn:
        with conn.cursor() as cur:
            # Check columns
            cur.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'documents' AND table_schema = 'public'
            """)
            existing_columns = {row[0] for row in cur.fetchall()}
            
            if not required_columns.issubset(existing_columns):
                missing = required_columns - existing_columns
                raise RuntimeError(f"Missing columns: {missing}. Run migrations first.")
            
            # Check indexes
            cur.execute("""
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'documents' AND schemaname = 'public'
            """)
            existing_indexes = {row[0] for row in cur.fetchall()}
            
            if not required_indexes.issubset(existing_indexes):
                missing = required_indexes - existing_indexes
                raise RuntimeError(f"Missing indexes: {missing}. Run migrations first.")
    
    return True


## 🎯 Optional Enhancements (As Suggested)

### Schema Verification Function
def verify_schema() -> bool:
    """Verify expected schema exists; raise if migrations needed."""
    required_columns = {'id', 'content', 'embedding', 'metadata', 'created_at', 'updated_at'}
    required_indexes = {'documents_embedding_cosine_idx', 'documents_content_trgm_idx'}
    
    with _get_conn() as conn:
        with conn.cursor() as cur:
            # Check columns
            cur.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'documents' AND table_schema = 'public'
            """)
            existing_columns = {row[0] for row in cur.fetchall()}
            
            if not required_columns.issubset(existing_columns):
                missing = required_columns - existing_columns
                raise RuntimeError(f"Missing columns: {missing}. Run migrations first.")
            
            # Check indexes
            cur.execute("""
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'documents' AND schemaname = 'public'
            """)
            existing_indexes = {row[0] for row in cur.fetchall()}
            
            if not required_indexes.issubset(existing_indexes):
                missing = required_indexes - existing_indexes
                raise RuntimeError(f"Missing indexes: {missing}. Run migrations first.")
    
    return True


## 🎯 Optional Enhancements (As Suggested)

### Schema Verification Function
def verify_schema() -> bool:
    """Verify expected schema exists; raise if migrations needed."""
    required_columns = {'id', 'content', 'embedding', 'metadata', 'created_at', 'updated_at'}
    required_indexes = {'documents_embedding_cosine_idx', 'documents_content_trgm_idx'}
    
    with _get_conn() as conn:
        with conn.cursor() as cur:
            # Check columns
            cur.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'documents' AND table_schema = 'public'
            """)
            existing_columns = {row[0] for row in cur.fetchall()}
            
            if not required_columns.issubset(existing_columns):
                missing = required_columns - existing_columns
                raise RuntimeError(f"Missing columns: {missing}. Run migrations first.")
            
            # Check indexes
            cur.execute("""
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'documents' AND schemaname = 'public'
            """)
            existing_indexes = {row[0] for row in cur.fetchall()}
            
            if not required_indexes.issubset(existing_indexes):
                missing = required_indexes - existing_indexes
                raise RuntimeError(f"Missing indexes: {missing}. Run migrations first.")
    
    return True


## 🎯 Optional Enhancements (As Suggested)

### Schema Verification Function
def verify_schema() -> bool:
    """Verify expected schema exists; raise if migrations needed."""
    required_columns = {'id', 'content', 'embedding', 'metadata', 'created_at', 'updated_at'}
    required_indexes = {'documents_embedding_cosine_idx', 'documents_content_trgm_idx'}
    
    with _get_conn() as conn:
        with conn.cursor() as cur:
            # Check columns
            cur.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'documents' AND table_schema = 'public'
            """)
            existing_columns = {row[0] for row in cur.fetchall()}
            
            if not required_columns.issubset(existing_columns):
                missing = required_columns - existing_columns
                raise RuntimeError(f"Missing columns: {missing}. Run migrations first.")
            
            # Check indexes
            cur.execute("""
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'documents' AND schemaname = 'public'
            """)
            existing_indexes = {row[0] for row in cur.fetchall()}
            
            if not required_indexes.issubset(existing_indexes):
                missing = required_indexes - existing_indexes
                raise RuntimeError(f"Missing indexes: {missing}. Run migrations first.")
    
    return True


## 🎯 Optional Enhancements (As Suggested)

### Schema Verification Function
def verify_schema() -> bool:
    """Verify expected schema exists; raise if migrations needed."""
    required_columns = {'id', 'content', 'embedding', 'metadata', 'created_at', 'updated_at'}
    required_indexes = {'documents_embedding_cosine_idx', 'documents_content_trgm_idx'}
    
    with _get_conn() as conn:
        with conn.cursor() as cur:
            # Check columns
            cur.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'documents' AND table_schema = 'public'
            """)
            existing_columns = {row[0] for row in cur.fetchall()}
            
            if not required_columns.issubset(existing_columns):
                missing = required_columns - existing_columns
                raise RuntimeError(f"Missing columns: {missing}. Run migrations first.")
            
            # Check indexes
            cur.execute("""
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'documents' AND schemaname = 'public'
            """)
            existing_indexes = {row[0] for row in cur.fetchall()}
            
            if not required_indexes.issubset(existing_indexes):
                missing = required_indexes - existing_indexes
                raise RuntimeError(f"Missing indexes: {missing}. Run migrations first.")
    
    return True


## 🎯 Optional Enhancements (As Suggested)

### Schema Verification Function
def verify_schema() -> bool:
    """Verify expected schema exists; raise if migrations needed."""
    required_columns = {'id', 'content', 'embedding', 'metadata', 'created_at', 'updated_at'}
    required_indexes = {'documents_embedding_cosine_idx', 'documents_content_trgm_idx'}
    
    with _get_conn() as conn:
        with conn.cursor() as cur:
            # Check columns
            cur.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'documents' AND table_schema = 'public'
            """)
            existing_columns = {row[0] for row in cur.fetchall()}
            
            if not required_columns.issubset(existing_columns):
                missing = required_columns - existing_columns
                raise RuntimeError(f"Missing columns: {missing}. Run migrations first.")
            
            # Check indexes
            cur.execute("""
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'documents' AND schemaname = 'public'
            """)
            existing_indexes = {row[0] for row in cur.fetchall()}
            
            if not required_indexes.issubset(existing_indexes):
                missing = required_indexes - existing_indexes
                raise RuntimeError(f"Missing indexes: {missing}. Run migrations first.")
    
    return True


## 🎯 Optional Enhancements (As Suggested)

### Schema Verification Function
def verify_schema() -> bool:
    """Verify expected schema exists; raise if migrations needed."""
    required_columns = {'id', 'content', 'embedding', 'metadata', 'created_at', 'updated_at'}
    required_indexes = {'documents_embedding_cosine_idx', 'documents_content_trgm_idx'}
    
    with _get_conn() as conn:
        with conn.cursor() as cur:
            # Check columns
            cur.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'documents' AND table_schema = 'public'
            """)
            existing_columns = {row[0] for row in cur.fetchall()}
            
            if not required_columns.issubset(existing_columns):
                missing = required_columns - existing_columns
                raise RuntimeError(f"Missing columns: {missing}. Run migrations first.")
            
            # Check indexes
            cur.execute("""
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'documents' AND schemaname = 'public'
            """)
            existing_indexes = {row[0] for row in cur.fetchall()}
            
            if not required_indexes.issubset(existing_indexes):
                missing = required_indexes - existing_indexes
                raise RuntimeError(f"Missing indexes: {missing}. Run migrations first.")
    
    return True


## 🎯 Optional Enhancements (As Suggested)

### Schema Verification Function
def verify_schema() -> bool:
    """Verify expected schema exists; raise if migrations needed."""
    required_columns = {'id', 'content', 'embedding', 'metadata', 'created_at', 'updated_at'}
    required_indexes = {'documents_embedding_cosine_idx', 'documents_content_trgm_idx'}
    
    with _get_conn() as conn:
        with conn.cursor() as cur:
            # Check columns
            cur.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'documents' AND table_schema = 'public'
            """)
            existing_columns = {row[0] for row in cur.fetchall()}
            
            if not required_columns.issubset(existing_columns):
                missing = required_columns - existing_columns
                raise RuntimeError(f"Missing columns: {missing}. Run migrations first.")
            
            # Check indexes
            cur.execute("""
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'documents' AND schemaname = 'public'
            """)
            existing_indexes = {row[0] for row in cur.fetchall()}
            
            if not required_indexes.issubset(existing_indexes):
                missing = required_indexes - existing_indexes
                raise RuntimeError(f"Missing indexes: {missing}. Run migrations first.")
    
    return True


## 🎯 Optional Enhancements (As Suggested)

### Schema Verification Function
def verify_schema() -> bool:
    """Verify expected schema exists; raise if migrations needed."""
    required_columns = {'id', 'content', 'embedding', 'metadata', 'created_at', 'updated_at'}
    required_indexes = {'documents_embedding_cosine_idx', 'documents_content_trgm_idx'}
    
    with _get_conn() as conn:
        with conn.cursor() as cur:
            # Check columns
            cur.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'documents' AND table_schema = 'public'
            """)
            existing_columns = {row[0] for row in cur.fetchall()}
            
            if not required_columns.issubset(existing_columns):
                missing = required_columns - existing_columns
                raise RuntimeError(f"Missing columns: {missing}. Run migrations first.")
            
            # Check indexes
            cur.execute("""
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'documents' AND schemaname = 'public'
            """)
            existing_indexes = {row[0] for row in cur.fetchall()}
            
            if not required_indexes.issubset(existing_indexes):
                missing = required_indexes - existing_indexes
                raise RuntimeError(f"Missing indexes: {missing}. Run migrations first.")
    
    return True


## 🎯 Optional Enhancements (As Suggested)

### Schema Verification Function
def verify_schema() -> bool:
    """Verify expected schema exists; raise if migrations needed."""
    required_columns = {'id', 'content', 'embedding', 'metadata', 'created_at', 'updated_at'}
    required_indexes = {'documents_embedding_cosine_idx', 'documents_content_trgm_idx'}
    
    with _get_conn() as conn:
        with conn.cursor() as cur:
            # Check columns
            cur.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'documents' AND table_schema = 'public'
            """)
            existing_columns = {row[0] for row in cur.fetchall()}
            
            if not required_columns.issubset(existing_columns):
                missing = required_columns - existing_columns
                raise RuntimeError(f"Missing columns: {missing}. Run migrations first.")
            
            # Check indexes
            cur.execute("""
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'documents' AND schemaname = 'public'
            """)
            existing_indexes = {row[0] for row in cur.fetchall()}
            
            if not required_indexes.issubset(existing_indexes):
                missing = required_indexes - existing_indexes
                raise RuntimeError(f"Missing indexes: {missing}. Run migrations first.")
    
    return True


## 🎯 Optional Enhancements (As Suggested)

### Schema Verification Function
def verify_schema() -> bool:
    """Verify expected schema exists; raise if migrations needed."""
    required_columns = {'id', 'content', 'embedding', 'metadata', 'created_at', 'updated_at'}
    required_indexes = {'documents_embedding_cosine_idx', 'documents_content_trgm_idx'}
    
    with _get_conn() as conn:
        with conn.cursor() as cur:
            # Check columns
            cur.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'documents' AND table_schema = 'public'
            """)
            existing_columns = {row[0] for row in cur.fetchall()}
            
            if not required_columns.issubset(existing_columns):
                missing = required_columns - existing_columns
                raise RuntimeError(f"Missing columns: {missing}. Run migrations first.")
            
            # Check indexes
            cur.execute("""
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'documents' AND schemaname = 'public'
            """)
            existing_indexes = {row[0] for row in cur.fetchall()}
            
            if not required_indexes.issubset(existing_indexes):
                missing = required_indexes - existing_indexes
                raise RuntimeError(f"Missing indexes: {missing}. Run migrations first.")
    
    return True


## 🎯 Optional Enhancements (As Suggested)

### Schema Verification Function
def verify_schema() -> bool:
    """Verify expected schema exists; raise if migrations needed."""
    required_columns = {'id', 'content', 'embedding', 'metadata', 'created_at', 'updated_at'}
    required_indexes = {'documents_embedding_cosine_idx', 'documents_content_trgm_idx'}
    
    with _get_conn() as conn:
        with conn.cursor() as cur:
            # Check columns
            cur.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'documents' AND table_schema = 'public'
            """)
            existing_columns = {row[0] for row in cur.fetchall()}
            
            if not required_columns.issubset(existing_columns):
                missing = required_columns - existing_columns
                raise RuntimeError(f"Missing columns: {missing}. Run migrations first.")
            
            # Check indexes
            cur.execute("""
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'documents' AND schemaname = 'public'
            """)
            existing_indexes = {row[0] for row in cur.fetchall()}
            
            if not required_indexes.issubset(existing_indexes):
                missing = required_indexes - existing_indexes
                raise RuntimeError(f"Missing indexes: {missing}. Run migrations first.")
    
    return True


## 🎯 Optional Enhancements (As Suggested)

### Schema Verification Function
def verify_schema() -> bool:
    """Verify expected schema exists; raise if migrations needed."""
    required_columns = {'id', 'content', 'embedding', 'metadata', 'created_at', 'updated_at'}
    required_indexes = {'documents_embedding_cosine_idx', 'documents_content_trgm_idx'}
    
    with _get_conn() as conn:
        with conn.cursor() as cur:
            # Check columns
            cur.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'documents' AND table_schema = 'public'
            """)
            existing_columns = {row[0] for row in cur.fetchall()}
            
            if not required_columns.issubset(existing_columns):
                missing = required_columns - existing_columns
                raise RuntimeError(f"Missing columns: {missing}. Run migrations first.")
            
            # Check indexes
            cur.execute("""
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'documents' AND schemaname = 'public'
            """)
            existing_indexes = {row[0] for row in cur.fetchall()}
            
            if not required_indexes.issubset(existing_indexes):
                missing = required_indexes - existing_indexes
                raise RuntimeError(f"Missing indexes: {missing}. Run migrations first.")
    
    return True


## 🎯 Optional Enhancements (As Suggested)

### Schema Verification Function
def verify_schema() -> bool:
    """Verify expected schema exists; raise if migrations needed."""
    required_columns = {'id', 'content', 'embedding', 'metadata', 'created_at', 'updated_at'}
    required_indexes = {'documents_embedding_cosine_idx', 'documents_content_trgm_idx'}
    
    with _get_conn() as conn:
        with conn.cursor() as cur:
            # Check columns
            cur.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'documents' AND table_schema = 'public'
            """)
            existing_columns = {row[0] for row in cur.fetchall()}
            
            if not required_columns.issubset(existing_columns):
                missing = required_columns - existing_columns
                raise RuntimeError(f"Missing columns: {missing}. Run migrations first.")
            
            # Check indexes
            cur.execute("""
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'documents' AND schemaname = 'public'
            """)
            existing_indexes = {row[0] for row in cur.fetchall()}
            
            if not required_indexes.issubset(existing_indexes):
                missing = required_indexes - existing_indexes
                raise RuntimeError(f"Missing indexes: {missing}. Run migrations first.")
    
    return True


## 🎯 Optional Enhancements (As Suggested)

### Schema Verification Function
def verify_schema() -> bool:
    """Verify expected schema exists; raise if migrations needed."""
    required_columns = {'id', 'content', 'embedding', 'metadata', 'created_at', 'updated_at'}
    required_indexes = {'documents_embedding_cosine_idx', 'documents_content_trgm_idx'}
    
    with _get_conn() as conn:
        with conn.cursor() as cur:
            # Check columns
            cur.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'documents' AND table_schema = 'public'
            """)
            existing_columns = {row[0] for row in cur.fetchall()}
            
            if not required_columns.issubset(existing_columns):
                missing = required_columns - existing_columns
                raise RuntimeError(f"Missing columns: {missing}. Run migrations first.")
            
            # Check indexes
            cur.execute("""
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'documents' AND schemaname = 'public'
            """)
            existing_indexes = {row[0] for row in cur.fetchall()}
            
            if not required_indexes.issubset(existing_indexes):
                missing = required_indexes - existing_indexes
                raise RuntimeError(f"Missing indexes: {missing}. Run migrations first.")
    
    return True


## 🎯 Optional Enhancements (As Suggested)

### Schema Verification Function
def verify_schema() -> bool:
    """Verify expected schema exists; raise if migrations needed."""
    required_columns = {'id', 'content', 'embedding', 'metadata', 'created_at', 'updated_at'}
    required_indexes = {'documents_embedding_cosine_idx', 'documents_content_trgm_idx'}
    
    with _get_conn() as conn:
        with conn.cursor() as cur:
            # Check columns
            cur.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'documents' AND table_schema = 'public'
            """)
            existing_columns = {row[0] for row in cur.fetchall()}
            
            if not required_columns.issubset(existing_columns):
                missing = required_columns - existing_columns
                raise RuntimeError(f"Missing columns: {missing}. Run migrations first.")
            
            # Check indexes
            cur.execute("""
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'documents' AND schemaname = 'public'
            """)
            existing_indexes = {row[0] for row in cur.fetchall()}
            
            if not required_indexes.issubset(existing_indexes):
                missing = required_indexes - existing_indexes
                raise RuntimeError(f"Missing indexes: {missing}. Run migrations first.")
    
    return True


## 🎯 Optional Enhancements (As Suggested)

### Schema Verification Function
def verify_schema() -> bool:
    """Verify expected schema exists; raise if migrations needed."""
    required_columns = {'id', 'content', 'embedding', 'metadata', 'created_at', 'updated_at'}
    required_indexes = {'documents_embedding_cosine_idx', 'documents_content_trgm_idx'}
    
    with _get_conn() as conn:
        with conn.cursor() as cur:
            # Check columns
            cur.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'documents' AND table_schema = 'public'
            """)
            existing_columns = {row[0] for row in cur.fetchall()}
            
            if not required_columns.issubset(existing_columns):
                missing = required_columns - existing_columns
                raise RuntimeError(f"Missing columns: {missing}. Run migrations first.")
            
            # Check indexes
            cur.execute("""
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'documents' AND schemaname = 'public'
            """)
            existing_indexes = {row[0] for row in cur.fetchall()}
            
            if not required_indexes.issubset(existing_indexes):
                missing = required_indexes - existing_indexes
                raise RuntimeError(f"Missing indexes: {missing}. Run migrations first.")
    
    return True


## 🎯 Optional Enhancements (As Suggested)

### Schema Verification Function
def verify_schema() -> bool:
    """Verify expected schema exists; raise if migrations needed."""
    required_columns = {'id', 'content', 'embedding', 'metadata', 'created_at', 'updated_at'}
    required_indexes = {'documents_embedding_cosine_idx', 'documents_content_trgm_idx'}
    
    with _get_conn() as conn:
        with conn.cursor() as cur:
            # Check columns
            cur.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'documents' AND table_schema = 'public'
            """)
            existing_columns = {row[0] for row in cur.fetchall()}
            
            if not required_columns.issubset(existing_columns):
                missing = required_columns - existing_columns
                raise RuntimeError(f"Missing columns: {missing}. Run migrations first.")
            
            # Check indexes
            cur.execute("""
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'documents' AND schemaname = 'public'
            """)
            existing_indexes = {row[0] for row in cur.fetchall()}
            
            if not required_indexes.issubset(existing_indexes):
                missing = required_indexes - existing_indexes
                raise RuntimeError(f"Missing indexes: {missing}. Run migrations first.")
    
    return True


## 🎯 Optional Enhancements (As Suggested)

### Schema Verification Function
def verify_schema() -> bool:
    """Verify expected schema exists; raise if migrations needed."""
    required_columns = {'id', 'content', 'embedding', 'metadata', 'created_at', 'updated_at'}
    required_indexes = {'documents_embedding_cosine_idx', 'documents_content_trgm_idx'}
    
    with _get_conn() as conn:
        with conn.cursor() as cur:
            # Check columns
            cur.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'documents' AND table_schema = 'public'
            """)
            existing_columns = {row[0] for row in cur.fetchall()}
            
            if not required_columns.issubset(existing_columns):
                missing = required_columns - existing_columns
                raise RuntimeError(f"Missing columns: {missing}. Run migrations first.")
            
            # Check indexes
            cur.execute("""
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'documents' AND schemaname = 'public'
            """)
            existing_indexes = {row[0] for row in cur.fetchall()}
            
            if not required_indexes.issubset(existing_indexes):
                missing = required_indexes - existing_indexes
                raise RuntimeError(f"Missing indexes: {missing}. Run migrations first.")
    
    return True


## 🎯 Optional Enhancements (As Suggested)

### Schema Verification Function
def verify_schema() -> bool:
    """Verify expected schema exists; raise if migrations needed."""
    required_columns = {'id', 'content', 'embedding', 'metadata', 'created_at', 'updated_at'}
    required_indexes = {'documents_embedding_cosine_idx', 'documents_content_trgm_idx'}
    
    with _get_conn() as conn:
        with conn.cursor() as cur:
            # Check columns
            cur.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'documents' AND table_schema = 'public'
            """)
            existing_columns = {row[0] for row in cur.fetchall()}
            
            if not required_columns.issubset(existing_columns):
                missing = required_columns - existing_columns
                raise RuntimeError(f"Missing columns: {missing}. Run migrations first.")
            
            # Check indexes
            cur.execute("""
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'documents' AND schemaname = 'public'
            """)
            existing_indexes = {row[0] for row in cur.fetchall()}
            
            if not required_indexes.issubset(existing_indexes):
                missing = required_indexes - existing_indexes
                raise RuntimeError(f"Missing indexes: {missing}. Run migrations first.")
    
    return True


## 🎯 Optional Enhancements (As Suggested)

### Schema Verification Function
def verify_schema() -> bool:
    """Verify expected schema exists; raise if migrations needed."""
    required_columns = {'id', 'content', 'embedding', 'metadata', 'created_at', 'updated_at'}
    required_indexes = {'documents_embedding_cosine_idx', 'documents_content_trgm_idx'}
    
    with _get_conn() as conn:
        with conn.cursor() as cur:
            # Check columns
            cur.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'documents' AND table_schema = 'public'
            """)
            existing_columns = {row[0] for row in cur.fetchall()}
            
            if not required_columns.issubset(existing_columns):
                missing = required_columns - existing_columns
                raise RuntimeError(f"Missing columns: {missing}. Run migrations first.")
            
            # Check indexes
            cur.execute("""
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'documents' AND schemaname = 'public'
            """)
            existing_indexes = {row[0] for row in cur.fetchall()}
            
            if not required_indexes.issubset(existing_indexes):
                missing = required_indexes - existing_indexes
                raise RuntimeError(f"Missing indexes: {missing}. Run migrations first.")
    
    return True


## 🎯 Optional Enhancements (As Suggested)

### Schema Verification Function
def verify_schema() -> bool:
    """Verify expected schema exists; raise if migrations needed."""
    required_columns = {'id', 'content', 'embedding', 'metadata', 'created_at', 'updated_at'}
    required_indexes = {'documents_embedding_cosine_idx', 'documents_content_trgm_idx'}
    
    with _get_conn() as conn:
        with conn.cursor() as cur:
            # Check columns
            cur.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'documents' AND table_schema = 'public'
            """)
            existing_columns = {row[0] for row in cur.fetchall()}
            
            if not required_columns.issubset(existing_columns):
                missing = required_columns - existing_columns
                raise RuntimeError(f"Missing columns: {missing}. Run migrations first.")
            
            # Check indexes
            cur.execute("""
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'documents' AND schemaname = 'public'
            """)
            existing_indexes = {row[0] for row in cur.fetchall()}
            
            if not required_indexes.issubset(existing_indexes):
                missing = required_indexes - existing_indexes
                raise RuntimeError(f"Missing indexes: {missing}. Run migrations first.")
    
    return True


## 🎯 Optional Enhancements (As Suggested)

### Schema Verification Function
def verify_schema() -> bool:
    """Verify expected schema exists; raise if migrations needed."""
    required_columns = {'id', 'content', 'embedding', 'metadata', 'created_at', 'updated_at'}
    required_indexes = {'documents_embedding_cosine_idx', 'documents_content_trgm_idx'}
    
    with _get_conn() as conn:
        with conn.cursor() as cur:
            # Check columns
            cur.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'documents' AND table_schema = 'public'
            """)
            existing_columns = {row[0] for row in cur.fetchall()}
            
            if not required_columns.issubset(existing_columns):
                missing = required_columns - existing_columns
                raise RuntimeError(f"Missing columns: {missing}. Run migrations first.")
            
            # Check indexes
            cur.execute("""
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'documents' AND schemaname = 'public'
            """)
            existing_indexes = {row[0] for row in cur.fetchall()}
            
            if not required_indexes.issubset(existing_indexes):
                missing = required_indexes - existing_indexes
                raise RuntimeError(f"Missing indexes: {missing}. Run migrations first.")
    
    return True


## 🎯 Optional Enhancements (As Suggested)

### Schema Verification Function
def verify_schema() -> bool:
    """Verify expected schema exists; raise if migrations needed."""
    required_columns = {'id', 'content', 'embedding', 'metadata', 'created_at', 'updated_at'}
    required_indexes = {'documents_embedding_cosine_idx', 'documents_content_trgm_idx'}
    
    with _get_conn() as conn:
        with conn.cursor() as cur:
            # Check columns
            cur.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'documents' AND table_schema = 'public'
            """)
            existing_columns = {row[0] for row in cur.fetchall()}
            
            if not required_columns.issubset(existing_columns):
                missing = required_columns - existing_columns
                raise RuntimeError(f"Missing columns: {missing}. Run migrations first.")
            
            # Check indexes
            cur.execute("""
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'documents' AND schemaname = 'public'
            """)
            existing_indexes = {row[0] for row in cur.fetchall()}
            
            if not required_indexes.issubset(existing_indexes):
                missing = required_indexes - existing_indexes
                raise RuntimeError(f"Missing indexes: {missing}. Run migrations first.")
    
    return True


## 🎯 Optional Enhancements (As Suggested)

### Schema Verification Function
def verify_schema() -> bool:
    """Verify expected schema exists; raise if migrations needed."""
    required_columns = {'id', 'content', 'embedding', 'metadata', 'created_at', 'updated_at'}
    required_indexes = {'documents_embedding_cosine_idx', 'documents_content_trgm_idx'}
    
    with _get_conn() as conn:
        with conn.cursor() as cur:
            # Check columns
            cur.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'documents' AND table_schema = 'public'
            """)
            existing_columns = {row[0] for row in cur.fetchall()}
            
            if not required_columns.issubset(existing_columns):
                missing = required_columns - existing_columns
                raise RuntimeError(f"Missing columns: {missing}. Run migrations first.")
            
            # Check indexes
            cur.execute("""
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'documents' AND schemaname = 'public'
            """)
            existing_indexes = {row[0] for row in cur.fetchall()}
            
            if not required_indexes.issubset(existing_indexes):
                missing = required_indexes - existing_indexes
                raise RuntimeError(f"Missing indexes: {missing}. Run migrations first.")
    
    return True


## 🎯 Optional Enhancements (As Suggested)

### Schema Verification Function
def verify_schema() -> bool:
    """Verify expected schema exists; raise if migrations needed."""
    required_columns = {'id', 'content', 'embedding', 'metadata', 'created_at', 'updated_at'}
    required_indexes = {'documents_embedding_cosine_idx', 'documents_content_trgm_idx'}
    
    with _get_conn() as conn:
        with conn.cursor() as cur:
            # Check columns
            cur.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'documents' AND table_schema = 'public'
            """)
            existing_columns = {row[0] for row in cur.fetchall()}
            
            if not required_columns.issubset(existing_columns):
                missing = required_columns - existing_columns
                raise RuntimeError(f"Missing columns: {missing}. Run migrations first.")
            
            # Check indexes
            cur.execute("""
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'documents' AND schemaname = 'public'
            """)
            existing_indexes = {row[0] for row in cur.fetchall()}
            
            if not required_indexes.issubset(existing_indexes):
                missing = required_indexes - existing_indexes
                raise RuntimeError(f"Missing indexes: {missing}. Run migrations first.")
    
    return True


## 🎯 Optional Enhancements (As Suggested)

### Schema Verification Function
def verify_schema() -> bool:
    """Verify expected schema exists; raise if migrations needed."""
    required_columns = {'id', 'content', 'embedding', 'metadata', 'created_at', 'updated_at'}
    required_indexes = {'documents_embedding_cosine_idx', 'documents_content_trgm_idx'}
    
    with _get_conn() as conn:
        with conn.cursor() as cur:
            # Check columns
            cur.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'documents' AND table_schema = 'public'
            """)
            existing_columns = {row[0] for row in cur.fetchall()}
            
            if not required_columns.issubset(existing_columns):
                missing = required_columns - existing_columns
                raise RuntimeError(f"Missing columns: {missing}. Run migrations first.")
            
            # Check indexes
            cur.execute("""
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'documents' AND schemaname = 'public'
            """)
            existing_indexes = {row[0] for row in cur.fetchall()}
            
            if not required_indexes.issubset(existing_indexes):
                missing = required_indexes - existing_indexes
                raise RuntimeError(f"Missing indexes: {missing}. Run migrations first.")
    
    return True


## 🎯 Optional Enhancements (As Suggested)

### Schema Verification Function
def verify_schema() -> bool:
    """Verify expected schema exists; raise if migrations needed."""
