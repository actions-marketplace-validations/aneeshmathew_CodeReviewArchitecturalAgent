import json
import re
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional


@dataclass
class DiagnosticError:
    """Standardized diagnostic error input for the LLM fix synthesis."""
    source_tool: str  # 'ruff' | 'mypy' | 'pytest' | 'syntax'
    file_path: str
    line_number: Optional[int] = None
    column_number: Optional[int] = None
    error_code: Optional[str] = None
    message: str = ""
    severity: str = "error"  # 'error' | 'warning'
    raw_trace: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ErrorParser:
    """Parses raw CLI output from Ruff, Mypy, and Pytest into structured diagnostic objects."""

    @staticmethod
    def parse_ruff(output_str: str) -> List[DiagnosticError]:
        """Parses Ruff stdout/stderr. Attempts JSON first, falls back to regex."""
        diagnostics: List[DiagnosticError] = []
        if not output_str.strip():
            return diagnostics

        try:
            items = json.loads(output_str)
            if isinstance(items, list):
                for item in items:
                    loc = item.get("location", {})
                    diagnostics.append(DiagnosticError(
                        source_tool="ruff",
                        file_path=item.get("filename", ""),
                        line_number=loc.get("row"),
                        column_number=loc.get("column"),
                        error_code=item.get("code"),
                        message=item.get("message", ""),
                        raw_trace=json.dumps(item)
                    ))
                return diagnostics
        except Exception:
            pass

        # Regex fallback for text output e.g.: path/to/file.py:12:5: E999 SyntaxError: ...
        pattern = re.compile(r"^([^:\n]+):(\d+):(?:(\d+):)?\s+([A-Z0-9]+)\s+(.+)$", re.MULTILINE)
        for match in pattern.finditer(output_str):
            file_path, line, col, code, msg = match.groups()
            diagnostics.append(DiagnosticError(
                source_tool="ruff",
                file_path=file_path.strip(),
                line_number=int(line),
                column_number=int(col) if col else None,
                error_code=code.strip(),
                message=msg.strip(),
                raw_trace=match.group(0)
            ))
        return diagnostics

    @staticmethod
    def parse_mypy(output_str: str) -> List[DiagnosticError]:
        """Parses Mypy output e.g.: path/file.py:10: error: Incompatible types in assignment [assignment]"""
        diagnostics: List[DiagnosticError] = []
        pattern = re.compile(
            r"^([^:\n]+):(\d+):(?:(\d+):)?\s*(error|warning|note):\s*(.*?)(?:\s*\[([a-zA-Z0-9_\-]+)\])?$",
            re.MULTILINE
        )
        for match in pattern.finditer(output_str):
            file_path, line, col, severity, msg, code = match.groups()
            if severity.lower() == "note":
                continue  # skip informational notes
            diagnostics.append(DiagnosticError(
                source_tool="mypy",
                file_path=file_path.strip(),
                line_number=int(line),
                column_number=int(col) if col else None,
                error_code=code.strip() if code else None,
                message=msg.strip(),
                severity=severity.lower(),
                raw_trace=match.group(0)
            ))
        return diagnostics

    @staticmethod
    def parse_pytest(output_str: str) -> List[DiagnosticError]:
        """Parses Pytest failure summaries and stack traces."""
        diagnostics: List[DiagnosticError] = []
        if not output_str.strip():
            return diagnostics

        # Match FAILED lines: FAILED tests/test_app.py::test_calculation - AssertionError: 4 != 5
        failed_pattern = re.compile(r"^FAILED\s+([^:\n]+)(?:::([^\s\-]+))?\s*(?:-\s*(.+))?$", re.MULTILINE)
        for match in failed_pattern.finditer(output_str):
            file_path, test_func, msg = match.groups()
            diagnostics.append(DiagnosticError(
                source_tool="pytest",
                file_path=file_path.strip(),
                line_number=None,
                error_code="TEST_FAILURE",
                message=f"Test '{test_func or 'unknown'}' failed: {msg or ''}".strip(),
                severity="error",
                raw_trace=match.group(0)
            ))

        # Check for pytest errors / exceptions with file & line
        tb_pattern = re.compile(r"File \"([^\"]+)\", line (\d+), in (\w+)\n\s*(.*?)\n([a-zA-Z0-9_]+Error: .*?)(?=\n\n|\Z)", re.DOTALL)
        for match in tb_pattern.finditer(output_str):
            file_path, line, func_name, code_snippet, error_msg = match.groups()
            diagnostics.append(DiagnosticError(
                source_tool="pytest",
                file_path=file_path.strip(),
                line_number=int(line),
                error_code="EXCEPTION",
                message=error_msg.strip(),
                severity="error",
                raw_trace=f"{code_snippet.strip()}\n{error_msg.strip()}"
            ))

        return diagnostics
