#!/usr/bin/env python3
"""
agents.builder – The Builder of containers, tests, and deployments.

Core contract:  handle(task: Dict) -> Dict

Supported tasks:
  * build : {'type':'build','repo':<path>,'tag':<tag>}
  * run   : {'type':'run','repo':<path>,'tag':<tag>,'port':<int|None>}
  * test  : {'type':'test','path':<path>}
"""

import json
import logging
import subprocess
from pathlib import Path
from typing import Any, Dict

# ─── Logger ────────────────────────────────────────────────────────────────
log = logging.getLogger("builder")
log.setLevel(logging.INFO)


class Builder:
    """The Builder of Aetherion - The Hands that Shape Reality"""
    
    def __init__(self):
        log.info("🔨 Builder awakens... Ready to craft and deploy...")
    
    # ------------------------------------------------------------------
    def _run_cmd(self, cmd: list[str]) -> str:
        """Execute a system command and return combined output."""
        log.debug("running: %s", cmd)
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            output = result.stdout.strip()
            if result.stderr.strip():
                output += "\n" + result.stderr.strip()
            return output
        except subprocess.CalledProcessError as e:
            log.error(f"Command failed: {' '.join(cmd)}")
            log.error(f"Exit code: {e.returncode}")
            log.error(f"Stderr: {e.stderr}")
            raise ValueError(f"Build operation failed: {e.stderr or e.stdout}")
        except Exception as e:
            log.error(f"Unexpected error running command: {e}")
            raise ValueError(f"Cannot execute build command: {str(e)}")

    # ------------------------------------------------------------------
    def build(self, repo: str, tag: str = "latest") -> Dict[str, str]:
        """
        Build a Docker image from the specified repository.
        
        Args:
            repo: Path to the repository containing Dockerfile
            tag: Tag to apply to the built image
            
        Returns:
            Dict containing build output
        """
        if not Path(repo).exists():
            raise ValueError(f"Repository path does not exist: {repo}")
            
        if not Path(repo, "Dockerfile").exists():
            raise ValueError(f"No Dockerfile found in {repo}")
            
        cmd = ["docker", "build", "-t", f"{repo}:{tag}", repo]
        out = self._run_cmd(cmd)
        log.info("docker build → %s:%s", repo, tag)
        return {"status": "built", "image": f"{repo}:{tag}", "output": out}

    # ------------------------------------------------------------------
    def run(self, repo: str, tag: str = "latest", port: int | None = None) -> Dict[str, str]:
        """
        Run a Docker container from the specified image.
        
        Args:
            repo: Repository name for the image
            tag: Image tag to run
            port: Optional port mapping
            
        Returns:
            Dict containing container ID and output
        """
        cmd = ["docker", "run", "-d"]
        if port:
            cmd += ["-p", f"{port}:{port}"]
        cmd += [f"{repo}:{tag}"]
        
        out = self._run_cmd(cmd)
        container_id = out.strip()
        
        log.info("docker run → %s:%s (container: %s)", repo, tag, container_id[:12])
        return {
            "status": "running",
            "container_id": container_id,
            "image": f"{repo}:{tag}",
            "port": port
        }

    # ------------------------------------------------------------------
    def test(self, path: str = "tests") -> Dict[str, Any]:
        """
        Run tests using pytest and return structured results.
        
        Args:
            path: Path to test directory or specific test file
            
        Returns:
            Dict containing test results
        """
        if not Path(path).exists():
            raise ValueError(f"Test path does not exist: {path}")
            
        cmd = ["pytest", path, "--json-report", "--json-report-file=test-report.json", "--no-cov", "-v"]
        
        try:
            out = self._run_cmd(cmd)
            
            # Try to read the JSON report if it exists
            report_file = Path("test-report.json")
            if report_file.exists():
                try:
                    with open(report_file) as f:
                        report_data = json.load(f)
                    # Clean up the temporary file
                    report_file.unlink()
                    
                    log.info("pytest → %s tests passed, %s failed", 
                            report_data.get("summary", {}).get("passed", 0),
                            report_data.get("summary", {}).get("failed", 0))
                    
                    return {
                        "status": "tested",
                        "report": report_data,
                        "raw_output": out
                    }
                except (json.JSONDecodeError, Exception) as e:
                    log.warning(f"Failed to parse test report: {e}")
            
            # Fallback to raw output
            return {
                "status": "tested",
                "report": {"raw": out},
                "raw_output": out
            }
            
        except ValueError as e:
            # Tests failed but we still want to return information
            log.warning(f"Tests failed: {e}")
            return {
                "status": "test_failures",
                "report": {"error": str(e)},
                "message": f"Tests encountered failures: {str(e)}"
            }

    # ------------------------------------------------------------------
    def handle(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Universal entry point for MetaForge.

        Supported tasks:
          * build : {'type':'build','repo':<path>,'tag':<tag>}
          * run   : {'type':'run','repo':<path>,'tag':<tag>,'port':<int|None>}
          * test  : {'type':'test','path':<path>}
        """
        task_type = task.get("type")
        
        try:
            if task_type == "build":
                return self.build(task["repo"], task.get("tag", "latest"))
            elif task_type == "run":
                return self.run(task["repo"], task.get("tag", "latest"), task.get("port"))
            elif task_type == "test":
                return self.test(task.get("path", "tests"))
            else:
                raise ValueError(f"Builder cannot handle task type: {task_type}")
                
        except Exception as e:
            log.error(f"Task handling failed for {task_type}: {e}")
            return {
                "status": "error",
                "task_type": task_type,
                "message": f"The Builder's tools fail: {str(e)}",
                "timestamp": __import__('datetime').datetime.utcnow().isoformat()
            }
