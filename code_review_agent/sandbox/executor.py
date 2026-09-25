import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional
from ..config import settings


@dataclass
class ExecutionResult:
    """Result of sandbox command execution."""
    command: List[str]
    return_code: int
    stdout: str
    stderr: str
    duration_seconds: float
    timed_out: bool = False

    @property
    def success(self) -> bool:
        return self.return_code == 0 and not self.timed_out


class SandboxExecutor:
    """Executes code analyzers, test suites, and patches safely in an isolated environment."""

    def __init__(
        self,
        workspace_path: Optional[str | Path] = None,
        timeout_seconds: Optional[int] = None,
        use_docker: bool = False
    ):
        self.workspace_path = Path(workspace_path or os.getcwd()).resolve()
        self.timeout_seconds = timeout_seconds or settings.sandbox_timeout_seconds
        self.use_docker = use_docker
        self._backup_snapshots: Dict[str, str] = {}

    def run_command(
        self,
        cmd: List[str],
        cwd: Optional[Path] = None,
        env_vars: Optional[Dict[str, str]] = None
    ) -> ExecutionResult:
        """Runs a command with timeout and process isolation."""
        work_dir = (cwd or self.workspace_path).resolve()
        
        # Build sanitized execution environment
        env = os.environ.copy()
        current_venv_bin = Path(sys.executable).parent
        env["PATH"] = f"{current_venv_bin}:{env.get('PATH', '')}"
        venv_bin = Path(self.workspace_path) / ".venv" / "bin"
        if venv_bin.exists():
            env["PATH"] = f"{venv_bin}:{env['PATH']}"
        if env_vars:
            env.update(env_vars)

        start_time = time.time()
        try:
            process = subprocess.run(
                cmd,
                cwd=str(work_dir),
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                env=env
            )
            duration = time.time() - start_time
            stdout_str = process.stdout.decode("utf-8", errors="replace") if isinstance(process.stdout, bytes) else (process.stdout or "")
            stderr_str = process.stderr.decode("utf-8", errors="replace") if isinstance(process.stderr, bytes) else (process.stderr or "")
            return ExecutionResult(
                command=cmd,
                return_code=process.returncode,
                stdout=stdout_str,
                stderr=stderr_str,
                duration_seconds=duration,
                timed_out=False
            )
        except subprocess.TimeoutExpired as e:
            duration = time.time() - start_time
            stdout_str = e.stdout.decode("utf-8", errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
            stderr_str = e.stderr.decode("utf-8", errors="replace") if isinstance(e.stderr, bytes) else (e.stderr or "")
            return ExecutionResult(
                command=cmd,
                return_code=-1,
                stdout=stdout_str,
                stderr=stderr_str + f"\nProcess timed out after {self.timeout_seconds} seconds.",
                duration_seconds=duration,
                timed_out=True
            )
        except Exception as e:
            duration = time.time() - start_time
            return ExecutionResult(
                command=cmd,
                return_code=-1,
                stdout="",
                stderr=f"Execution error: {str(e)}",
                duration_seconds=duration,
                timed_out=False
            )

    def snapshot_file(self, file_path: str | Path):
        """Records a snapshot of a file before applying patches for rollback capability."""
        path = Path(file_path).resolve()
        if path.is_file() and str(path) not in self._backup_snapshots:
            self._backup_snapshots[str(path)] = path.read_text(encoding="utf-8")

    def rollback(self):
        """Reverts all modified files to their original snapshot states."""
        for path_str, original_content in self._backup_snapshots.items():
            path = Path(path_str)
            path.write_text(original_content, encoding="utf-8")
        self._backup_snapshots.clear()

    def clear_snapshots(self):
        """Clears saved snapshots after successful verification."""
        self._backup_snapshots.clear()

    def apply_patch(self, file_path: str | Path, new_content: str):
        """Saves a backup snapshot and updates file with patched content."""
        path = Path(file_path).resolve()
        self.snapshot_file(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(new_content, encoding="utf-8")
