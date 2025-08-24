#!/usr/bin/env bash
set -e

# 1️⃣ Prepare virtual env
python3 -m venv .venv
source .venv/bin/activate

# 2️⃣ Install Python deps
pip install -r requirements.txt
pip install -e .

# 3️⃣ Bring up the runtime stack
docker compose up -d

# 4️⃣ Wait for services to become healthy
echo "Waiting for Ollama..."
while ! curl -s http://localhost:11434/api/ping | jq -e .up > /dev/null 2>&1; do sleep 1; done
echo "Ollama ready!"

echo "Waiting for Qdrant..."
while ! curl -s http://localhost:6333/ping | jq -e .healthy > /dev/null 2>&1; do sleep 1; done
echo "Qdrant ready!"

echo "Setup complete. Run the demo: python run_server.py"