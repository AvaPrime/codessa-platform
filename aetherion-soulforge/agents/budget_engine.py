#!/usr/bin/env python3
# agents/budget_engine.py
import json
import os
import tempfile
import logging
from datetime import datetime
from typing import List, Dict, Any

class BudgetEngine:
    def __init__(self, log_file: str = "budget_log.json", daily_limit: float = 1.0):
        self.log_file = log_file
        self.daily_limit = daily_limit
        self.entries: List[Dict[str, Any]] = []  # list of dicts, stored in file
        self._load_entries()

    def record(self, task_type: str, cost: float, agent: str, model: str | None):
        entry = {
            "ts": datetime.utcnow().isoformat(),
            "type": task_type,
            "agent": agent,
            "model": model,
            "cost": cost,
        }
        self.entries.append(entry)
        self._persist()

    def _load_entries(self):
        """Load entries from file with error handling."""
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, 'r') as f:
                    self.entries = json.load(f)
                logging.info(f"Loaded {len(self.entries)} budget entries from {self.log_file}")
            except (json.JSONDecodeError, IOError) as e:
                logging.error(f"Failed to load budget entries: {e}")
                # Create backup of corrupted file
                if os.path.exists(self.log_file):
                    backup_file = f"{self.log_file}.backup.{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
                    os.rename(self.log_file, backup_file)
                    logging.info(f"Corrupted budget file backed up to {backup_file}")
                self.entries = []

    def _persist(self):
        """Persist entries to file using atomic writes to prevent corruption."""
        try:
            # Create temporary file in the same directory as the target file
            dir_name = os.path.dirname(self.log_file) or '.'
            with tempfile.NamedTemporaryFile(mode='w', dir=dir_name, delete=False, suffix='.tmp') as temp_file:
                json.dump(self.entries, temp_file, indent=2)
                temp_file.flush()
                os.fsync(temp_file.fileno())  # Ensure data is written to disk
                temp_name = temp_file.name
            
            # Atomic move (rename) to replace the original file
            if os.name == 'nt':  # Windows
                # On Windows, we need to remove the target first
                if os.path.exists(self.log_file):
                    os.remove(self.log_file)
            os.rename(temp_name, self.log_file)
            
        except Exception as e:
            logging.error(f"Failed to persist budget entries: {e}")
            # Clean up temporary file if it exists
            try:
                if 'temp_name' in locals() and os.path.exists(temp_name):
                    os.remove(temp_name)
            except Exception:
                pass
            raise

    def total_today(self) -> float:
        today = datetime.utcnow().date().isoformat()
        return sum(e["cost"] for e in self.entries if e["ts"].startswith(today))

    def exceed_limit(self) -> bool:
        return self.total_today() > self.daily_limit
        
    # Legacy method for backward compatibility
    def add(self, cost):
        self.record("unknown", cost, "unknown", None)
        
    # Legacy method for backward compatibility
    def get_total(self):
        return self.total_today()