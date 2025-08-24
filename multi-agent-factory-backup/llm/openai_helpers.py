import os
from typing import List

# Use the modern OpenAI SDK
try:
    from openai import OpenAI
    _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
except Exception:
    _client = None

EMBED_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
GEN_MODEL   = os.getenv("GEN_MODEL", "gpt-4o-mini")

def embed_text(text: str) -> List[float]:
    """
    Returns a 1536-dim embedding by default. Falls back to zeros if no API key.
    """
    if not _client:
        return [0.0] * 1536
    text = text.replace("\n", " ")
    emb = _client.embeddings.create(model=EMBED_MODEL, input=text).data[0].embedding
    return emb

def generate_markdown(prompt: str) -> str:
    """
    Simple non-streaming completion. Falls back to a stub if no API key.
    """
    if not _client:
        return f"# Draft (offline)\n\n{prompt[:500]}\n\n> [No OPENAI_API_KEY set – returning stub.]"
    resp = _client.chat.completions.create(
        model=GEN_MODEL,
        messages=[{"role":"system","content":"You are a precise technical writer. Output clean, well-structured Markdown."},
                  {"role":"user","content":prompt}],
        temperature=0.2
    )
    return resp.choices[0].message.content