from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
from ..sandbox.executor import SandboxExecutor
from .error_parser import DiagnosticError, ErrorParser


@dataclass
class StaticAnalysisResult:
    """Consolidated result from running static analyzers and test suites."""
    success: bool
    errors: List[DiagnosticError] = field(default_factory=list)
    ruff_output: str = ""
    mypy_output: str = ""
    pytest_output: str = ""
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "error_count": len(self.errors),
            "errors": [e.to_dict() for e in self.errors],
            "summary": self.summary,
            "raw_outputs": {
                "ruff": self.ruff_output,
                "mypy": self.mypy_output,
                "pytest": self.pytest_output,
            }
        }


class StaticAnalysisRunner:
    """Orchestrates Ruff, Mypy, and Pytest runs inside the sandbox."""

    def __init__(self, sandbox: Optional[SandboxExecutor] = None):
        self.sandbox = sandbox or SandboxExecutor()
        self.parser = ErrorParser()

    def run_all(
        self,
        target_files: Optional[List[str]] = None,
        test_path: Optional[str] = None
    ) -> StaticAnalysisResult:
        """Executes all linters, type checkers, and test runners."""
        errors: List[DiagnosticError] = []

        # 1. Run Ruff
        ruff_res = self.run_ruff(target_files)
        errors.extend(self.parser.parse_ruff(ruff_res.stdout or ruff_res.stderr))

        # 2. Run Mypy
        mypy_res = self.run_mypy(target_files)
        errors.extend(self.parser.parse_mypy(mypy_res.stdout or mypy_res.stderr))

        # 3. Run Pytest if test_path specified or tests/ directory exists
        pytest_res = self.run_pytest(test_path)
        if pytest_res:
            errors.extend(self.parser.parse_pytest(pytest_res.stdout or pytest_res.stderr))

        success = len(errors) == 0
        summary = (
            "All static checks and tests passed cleanly."
            if success
            else f"Static analysis identified {len(errors)} diagnostic error(s)."
        )

        return StaticAnalysisResult(
            success=success,
            errors=errors,
            ruff_output=ruff_res.stdout + "\n" + ruff_res.stderr,
            mypy_output=mypy_res.stdout + "\n" + mypy_res.stderr,
            pytest_output=(pytest_res.stdout + "\n" + pytest_res.stderr) if pytest_res else "",
            summary=summary
        )

    def run_ruff(self, target_files: Optional[List[str]] = None):
        """Runs Ruff check with JSON output format."""
        cmd = ["ruff", "check", "--output-format=json"]
        if target_files:
            cmd.extend(target_files)
        else:
            cmd.append(".")
        return self.sandbox.run_command(cmd)

    def run_mypy(self, target_files: Optional[List[str]] = None):
        """Runs Mypy with column numbers and non-interactive output."""
        cmd = ["mypy", "--show-column-numbers", "--no-error-summary"]
        if target_files:
            cmd.extend(target_files)
        else:
            cmd.append(".")
        return self.sandbox.run_command(cmd)

    def run_pytest(self, test_path: Optional[str] = None):
        """Runs Pytest against test path or auto-detected tests directory."""
        path_to_test = test_path
        if not path_to_test:
            candidate = self.sandbox.workspace_path / "tests"
            if candidate.exists():
                path_to_test = str(candidate)
            else:
                test_files = list(self.sandbox.workspace_path.glob("test_*.py")) + list(self.sandbox.workspace_path.glob("*_test.py"))
                if test_files:
                    path_to_test = "."
                else:
                    return None

        cmd = ["pytest", "-v", path_to_test]
        return self.sandbox.run_command(cmd)
