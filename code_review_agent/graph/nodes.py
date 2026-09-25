import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from ..analyzer.error_parser import DiagnosticError
from ..analyzer.runner import StaticAnalysisRunner
from ..config import settings
from ..ingestion.ast_parser import ASTParser
from ..ingestion.chunker import CodeChunker
from ..ingestion.vector_store import CodeVectorStore
from ..llm.gemini_client import GeminiCodeReviewer
from ..sandbox.executor import SandboxExecutor
from ..state import AuditState

logger = logging.getLogger(__name__)


def get_shared_components(state: AuditState):
    """Initializes or retrieves shared components based on workspace path."""
    workspace = state.get("workspace_path", ".")
    sandbox = SandboxExecutor(workspace_path=workspace)
    runner = StaticAnalysisRunner(sandbox=sandbox)
    reviewer = GeminiCodeReviewer()
    return workspace, sandbox, runner, reviewer


def index_repo_ast_node(state: AuditState) -> Dict[str, Any]:
    """Node: Indexes repository, parses AST symbols, and chunks code for vector RAG."""
    workspace = state.get("workspace_path", ".")
    ws_path = Path(workspace).resolve()

    parser = ASTParser()
    chunker = CodeChunker(parser=parser)
    vector_store = CodeVectorStore()

    changed_files = state.get("changed_files", [])
    if not changed_files:
        # If no changed files provided, scan all python files under workspace
        all_py = [str(p.relative_to(ws_path)) for p in ws_path.rglob("*.py") if not any(x in p.parts for x in [".venv", "venv", ".git", "__pycache__"])]
        changed_files = all_py

    all_symbols = []
    all_chunks = []
    for rel_path in changed_files:
        full_path = ws_path / rel_path
        if full_path.exists():
            symbols = parser.parse_file(full_path)
            chunks = chunker.chunk_file(full_path)
            all_symbols.extend(symbols)
            all_chunks.extend(chunks)

    vector_store.index_chunks(all_chunks)
    call_graph = parser.build_call_graph(all_symbols)

    ast_summary = {
        "indexed_files": len(changed_files),
        "total_symbols": len(all_symbols),
        "symbol_names": [s.name for s in all_symbols],
        "call_graph": call_graph,
    }

    return {
        "changed_files": changed_files,
        "ast_summary": ast_summary,
        "status": "indexed",
        "retry_count": state.get("retry_count", 0),
    }


def run_static_analyzers_node(state: AuditState) -> Dict[str, Any]:
    """Node: Runs Ruff, Mypy, and Pytest to detect bugs and architectural regressions."""
    workspace, sandbox, runner, _ = get_shared_components(state)
    changed_files = state.get("changed_files", [])

    result = runner.run_all(target_files=changed_files)
    raw_errors = [e.to_dict() for e in result.errors]

    return {
        "static_errors": raw_errors,
        "test_results": result.to_dict(),
        "status": "analyzing",
    }


def generate_lgtm_node(state: AuditState) -> Dict[str, Any]:
    """Node: Generates LGTM architectural summary when no issues are found."""
    _, _, _, reviewer = get_shared_components(state)
    changed_files = state.get("changed_files", [])
    ast_summary = state.get("ast_summary", {})

    summary = reviewer.generate_lgtm_summary(changed_files, ast_summary)

    return {
        "lgtm_summary": summary,
        "status": "success",
        "comment_posted": True,
    }


def synthesize_fix_node(state: AuditState) -> Dict[str, Any]:
    """Node: Synthesizes automated fixes for detected errors using Gemini 3.5 Flash-Lite."""
    workspace, sandbox, _, reviewer = get_shared_components(state)
    ws_path = Path(workspace).resolve()

    raw_errors = state.get("static_errors", [])
    errors = [
        DiagnosticError(
            source_tool=e["source_tool"],
            file_path=e["file_path"],
            line_number=e.get("line_number"),
            column_number=e.get("column_number"),
            error_code=e.get("error_code"),
            message=e.get("message", ""),
            severity=e.get("severity", "error"),
            raw_trace=e.get("raw_trace", "")
        )
        for e in raw_errors
    ]

    # Group errors by file, mapping test failures to source implementation files
    errors_by_file: Dict[str, List[DiagnosticError]] = {}
    changed_files = state.get("changed_files", [])

    for err in errors:
        f_name = err.file_path
        if not f_name:
            continue

        path_obj = Path(f_name)
        # If the error is reported on a test file, map it back to the implementation file being audited
        if (path_obj.name.startswith("test_") or path_obj.name.endswith("_test.py")) and changed_files:
            mapped_file = None
            stripped_name = path_obj.name.replace("test_", "")
            for cf in changed_files:
                if Path(cf).name == stripped_name or stripped_name in Path(cf).name:
                    mapped_file = cf
                    break

            if not mapped_file:
                for symbol in state.get("ast_summary", {}).get("symbol_names", []):
                    if symbol in err.message or symbol in err.raw_trace:
                        for cf in changed_files:
                            mapped_file = cf
                            break
                        if mapped_file:
                            break

            if not mapped_file:
                for cf in changed_files:
                    if not (Path(cf).name.startswith("test_") or Path(cf).name.endswith("_test.py")):
                        mapped_file = cf
                        break

            if mapped_file:
                f_name = mapped_file

        errors_by_file.setdefault(f_name, []).append(err)

    suggested_patches = []
    is_structural = False
    retry_count = state.get("retry_count", 0) + 1

    for f_path_str, file_errors in errors_by_file.items():
        # Resolve full path
        target_path = Path(f_path_str)
        if not target_path.is_absolute():
            target_path = ws_path / target_path

        if not target_path.exists():
            continue

        orig_content = target_path.read_text(encoding="utf-8")
        patch = reviewer.synthesize_fix(
            file_path=str(target_path),
            file_content=orig_content,
            errors=file_errors,
            ast_summary=state.get("ast_summary", {}),
            retry_count=retry_count - 1
        )

        if patch.is_structural:
            is_structural = True

        suggested_patches.append({
            "file_path": str(target_path),
            "original": patch.original_code,
            "patched": patch.patched_code,
            "explanation": patch.explanation,
        })

        # Apply patch to sandbox
        sandbox.apply_patch(target_path, patch.patched_code)

    return {
        "suggested_patches": suggested_patches,
        "is_structural_change": is_structural,
        "retry_count": retry_count,
        "status": "synthesizing",
    }


def run_tests_node(state: AuditState) -> Dict[str, Any]:
    """Node: Re-runs the test suite in the sandbox against the newly synthesized patches."""
    workspace, sandbox, runner, _ = get_shared_components(state)
    changed_files = state.get("changed_files", [])

    result = runner.run_all(target_files=changed_files)
    raw_errors = [e.to_dict() for e in result.errors]

    return {
        "static_errors": raw_errors,
        "test_results": result.to_dict(),
        "status": "tested",
    }


def human_approval_node(state: AuditState) -> Dict[str, Any]:
    """Node: Pauses or checks approval for critical structural code modifications."""
    is_approved = state.get("is_approved_by_human", False)

    # In non-interactive or pre-approved modes, approval can be granted
    if not settings.require_human_approval_for_structural_changes:
        is_approved = True

    return {
        "is_approved_by_human": is_approved,
        "status": "awaiting_approval" if not is_approved else "approved",
    }


def publish_pr_node(state: AuditState) -> Dict[str, Any]:
    """Node: Creates a pull request or commits verified self-corrected patches."""
    workspace, sandbox, _, _ = get_shared_components(state)
    # Clear rollback snapshots since fixes passed
    sandbox.clear_snapshots()

    patches = state.get("suggested_patches", [])
    summary = (
        f"### 🚀 Self-Correction Successful\n\n"
        f"- Applied and verified {len(patches)} patch(es).\n"
        f"- All test suites passed after {state.get('retry_count', 1)} iteration(s).\n"
    )

    return {
        "lgtm_summary": summary,
        "status": "complete",
        "comment_posted": True,
    }


def failure_report_node(state: AuditState) -> Dict[str, Any]:
    """Node: Handles terminal failure when self-correction loop limit is reached."""
    workspace, sandbox, _, _ = get_shared_components(state)
    # Rollback files to initial state to prevent leaving broken code
    sandbox.rollback()

    errors = state.get("static_errors", [])
    summary = (
        f"### ❌ Self-Correction Halted\n\n"
        f"- Maximum retries ({settings.max_retries}) reached without resolving all errors.\n"
        f"- Remaining issues ({len(errors)}):\n"
    )
    for err in errors[:5]:
        summary += f"  - [{err.get('source_tool')}] {err.get('file_path')}:{err.get('line_number')}: {err.get('message')}\n"

    return {
        "lgtm_summary": summary,
        "status": "failed",
    }
