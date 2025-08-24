#!/usr/bin/env python3
"""Generate JSON schemas for non-Python consumers"""

import json
import os
from pathlib import Path
from typing import Dict, Any

from config.schemas.task_message import TaskMessage
from config.schemas.result_message import ResultMessage
from config.schemas.status_message import StatusMessage, HeartbeatMessage
from config.schemas.security import SignedEnvelope

def generate_json_schemas():
    """Generate JSON schemas for all message types"""
    
    schemas = {
        "task@1.0": TaskMessage.model_json_schema(),
        "result@1.0": ResultMessage.model_json_schema(),
        "status@1.0": StatusMessage.model_json_schema(),
        "heartbeat@1.0": HeartbeatMessage.model_json_schema(),
        "envelope@2.0": SignedEnvelope.model_json_schema()
    }
    
    # Create schemas directory
    schema_dir = Path("config/generated_schemas")
    schema_dir.mkdir(exist_ok=True)
    
    # Write individual schema files
    for schema_id, schema in schemas.items():
        schema_file = schema_dir / f"{schema_id.replace('@', '_v')}.json"
        with open(schema_file, 'w') as f:
            json.dump(schema, f, indent=2)
        print(f"Generated {schema_file}")
    
    # Write combined schema registry
    registry = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "Multi-Agent Factory Message Schema Registry",
        "version": "1.0",
        "schemas": schemas
    }
    
    registry_file = schema_dir / "registry.json"
    with open(registry_file, 'w') as f:
        json.dump(registry, f, indent=2)
    print(f"Generated {registry_file}")

if __name__ == "__main__":
    generate_json_schemas()