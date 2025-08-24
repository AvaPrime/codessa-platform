#!/usr/bin/env python3
"""
agents.validator – The Validator of Aetherion.
Runs tests, linters, and returns structured JSON reports.

Core contract:  handle(task: Dict) -> Dict

Supported tasks:
  * tests : {'type': 'tests', 'path': <test_path>}
  * lint  : {'type': 'lint', 'path': <source_path>}
"""

import json
import logging
import subprocess
from pathlib import Path
from typing import Any, Dict

# ─── Logger ────────────────────────────────────────────────────────────────
log = logging.getLogger("validator")
log.setLevel(logging.INFO)


class Validator:
    """The Validator of Aetherion - The Watcher that Ensures Quality"""
    
    def __init__(self):
        log.info("🔍 Validator awakens... Standards shall be maintained...")
    
    def _run_cmd(self, cmd: list[str]) -> str:
        """Execute a command and return combined stdout/stderr."""
        log.debug("running: %s", cmd)
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            # Combine stdout and stderr for comprehensive output
            output = result.stdout.strip()
            if result.stderr.strip():
                output += "\n" + result.stderr.strip()
            return output
        except Exception as e:
            log.error(f"Command execution failed: {e}")
            raise ValueError(f"Cannot execute validation command: {str(e)}")

    # ------------------------------------------------------------------
    def tests(self, path: str = "tests") -> Dict[str, Any]:
        """
        Run pytest and return structured test results.
        
        Args:
            path: Path to test directory or specific test file
            
        Returns:
            Dict containing test results and metadata
        """
        if not Path(path).exists():
            return {
                "status": "error",
                "message": f"Test path does not exist: {path}",
                "path": path
            }
            
        cmd = ["pytest", path, "--json-report", "--json-report-file=validation-report.json", "--no-cov", "-v"]
        out = self._run_cmd(cmd)
        
        # Try to parse the JSON report
        report_file = Path("validation-report.json")
        if report_file.exists():
            try:
                with open(report_file) as f:
                    report_data = json.load(f)
                # Clean up temporary file
                report_file.unlink()
                
                summary = report_data.get("summary", {})
                passed = summary.get("passed", 0)
                failed = summary.get("failed", 0)
                total = summary.get("total", 0)
                
                log.info("pytest → %d/%d tests passed", passed, total)
                
                return {
                    "status": "completed",
                    "path": path,
                    "summary": {
                        "total": total,
                        "passed": passed,
                        "failed": failed,
                        "success_rate": (passed / total * 100) if total > 0 else 0
                    },
                    "report": report_data,
                    "raw_output": out
                }
            except (json.JSONDecodeError, Exception) as e:
                log.warning(f"Failed to parse test report: {e}")
        
        # Fallback to raw output analysis
        lines = out.split('\n')
        summary_lines = [line for line in lines if 'passed' in line or 'failed' in line]
        
        return {
            "status": "completed",
            "path": path,
            "report": {"raw": out, "summary_lines": summary_lines},
            "raw_output": out
        }

    # ------------------------------------------------------------------
    def lint(self, path: str = ".") -> Dict[str, Any]:
        """
        Run linting tools and return structured results.
        
        Args:
            path: Path to source code to lint
            
        Returns:
            Dict containing lint results
        """
        if not Path(path).exists():
            return {
                "status": "error",
                "message": f"Lint path does not exist: {path}",
                "path": path
            }
        
        # Try multiple linters
        results = {}
        
        # Try ruff first (modern, fast Python linter)
        try:
            cmd = ["ruff", "check", path, "--output-format=json"]
            out = self._run_cmd(cmd)
            
            # Try to parse JSON output
            try:
                lint_data = json.loads(out) if out.strip() else []
                results["ruff"] = {
                    "status": "success",
                    "issues": lint_data,
                    "issue_count": len(lint_data) if isinstance(lint_data, list) else 0
                }
            except json.JSONDecodeError:
                results["ruff"] = {
                    "status": "success",
                    "raw_output": out,
                    "issue_count": len([line for line in out.split('\n') if line.strip()])
                }
                
            log.info("ruff lint → %d issues found", results["ruff"].get("issue_count", 0))
            
        except Exception as e:
            # Try flake8 as fallback
            try:
                cmd = ["flake8", path, "--format=json"]
                out = self._run_cmd(cmd)
                results["flake8"] = {"status": "success", "raw_output": out}
                log.info("flake8 lint → completed (ruff unavailable)")
            except Exception:
                results["lint"] = {
                    "status": "error",
                    "message": f"No suitable linter found (tried ruff, flake8): {str(e)}"
                }
        
        # Calculate overall status
        total_issues = sum(r.get("issue_count", 0) for r in results.values())
        overall_status = "clean" if total_issues == 0 else "issues_found"
        
        return {
            "status": overall_status,
            "path": path,
            "total_issues": total_issues,
            "linters": results,
            "timestamp": __import__('datetime').datetime.utcnow().isoformat()
        }

    # ------------------------------------------------------------------
    def handle(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Universal entry point for MetaForge.

        Supported tasks:
          * tests : {'type': 'tests', 'path': <test_path>}
          * lint  : {'type': 'lint', 'path': <source_path>}
        """
        task_type = task.get("type")
        
        try:
            if task_type == "tests":
                return self.tests(task.get("path", "tests"))
            elif task_type == "lint":
                return self.lint(task.get("path", "."))
            else:
                raise ValueError(f"Validator cannot handle task type: {task_type}")
                
        except Exception as e:
            log.error(f"Task handling failed for {task_type}: {e}")
            return {
                "status": "error",
                "task_type": task_type,
                "message": f"The Validator's scrutiny fails: {str(e)}",
                "timestamp": __import__('datetime').datetime.utcnow().isoformat()
            }
