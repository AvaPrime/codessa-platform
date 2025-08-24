# File: scripts/generate_json_schemas.py
# Purpose: Emit JSON Schemas for non-Python consumers and drift detection in CI/pre-commit.

from __future__ import annotations
import json, pathlib
from config.schemas.messages import TaskMessage, ResultMessage, StatusMessage, HeartbeatMessage

def main() -> None:
    out = pathlib.Path("config/schemas/json")
    out.mkdir(parents=True, exist_ok=True)
    mapping = {
        "task@1.0": TaskMessage,
        "result@1.0": ResultMessage,
        "status@1.0": StatusMessage,
        "heartbeat@1.0": HeartbeatMessage,
    }
    for name, model in mapping.items():
        (out / f"{name}.json").write_text(json.dumps(model.model_json_schema(), indent=2))
    print(f"Wrote {len(mapping)} schema(s) to {out}")

if __name__ == "__main__":
    main()
