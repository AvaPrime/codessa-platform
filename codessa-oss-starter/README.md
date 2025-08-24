# Codessa OSS Starter

Production-minded agent/RAG skeleton built on **LangGraph + Temporal + PydanticAI (MCP) + pgvector + vLLM/TGI + FastAPI**, with **Guardrails** and **Langfuse** hooks.

## Quick start

```bash
# 1) copy env
cp .env.example .env

# 2) run services (db + api)
docker compose -f infra/docker-compose.yml up --build -d

# 3) (optional) create pgvector extension if not created by init script
# docker exec -it <db_container> psql -U postgres -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

See `rag/ingest.py` for a minimal ingestion path to pgvector and `orchestration/` for LangGraph+Temporal stubs.
