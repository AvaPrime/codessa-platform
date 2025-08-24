# Minimal ingestion: chunk -> embed -> upsert to pgvector via LangChain
import os, glob
from langchain_postgres.vectorstores import PGVector
from langchain.embeddings.openai import OpenAIEmbeddings

CONN = f"postgresql+psycopg://{os.getenv('PGUSER','postgres')}:{os.getenv('PGPASSWORD','postgres')}@" \       f"{os.getenv('PGHOST','localhost')}:{os.getenv('PGPORT','5432')}/{os.getenv('PGDATABASE','postgres')}"
COLLECTION = os.getenv("COLLECTION_NAME", "docs")

def read_texts(path="data/*.txt"):
    texts = []
    for fp in glob.glob(path):
        with open(fp, "r", encoding="utf-8") as f:
            texts.append(f.read())
    return texts

def main():
    texts = read_texts()
    if not texts:
        print("No texts found under data/*.txt")
        return
    embeddings = OpenAIEmbeddings(model=os.getenv("EMBEDDINGS_MODEL","text-embedding-3-small"),
                                  openai_api_base=os.getenv("OPENAI_API_BASE"),
                                  openai_api_key=os.getenv("OPENAI_API_KEY","sk-dummy"))
    PGVector.from_texts(texts, embedding=embeddings, connection_string=CONN, collection_name=COLLECTION)
    print(f"Ingested {len(texts)} docs into collection '{COLLECTION}'.")

if __name__ == "__main__":
    main()
