import argparse
import json
import os
import sys
from pathlib import Path
from .config import settings
from .graph.workflow import create_audit_graph
from .ingestion.ast_parser import ASTParser
from .ingestion.chunker import CodeChunker
from .state import AuditState


def run_audit(args):
    """Executes the full LangGraph self-correcting audit loop on a workspace."""
    workspace = Path(args.path).resolve()
    if not workspace.exists():
        print(f"Error: Path '{workspace}' does not exist.")
        sys.exit(1)

    print("=" * 60)
    print("🚀 Self-Correcting Code Review & Architectural Audit Agent")
    print(f"📂 Workspace: {workspace}")
    print(f"🤖 LLM Model: {settings.gemini_model} (Google Gemini Free Tier)")
    print(f"🔄 Max Retries: {settings.max_retries}")
    print("=" * 60)

    initial_state: AuditState = {
        "repo_url": str(workspace),
        "commit_sha": "HEAD",
        "workspace_path": str(workspace),
        "changed_files": args.files if args.files else [],
        "retry_count": 0,
        "is_approved_by_human": args.auto_approve,
        "status": "started",
    }

    graph = create_audit_graph()
    final_state = graph.invoke(initial_state)

    print("\n" + "=" * 60)
    print(f"🏁 Audit Status: {final_state.get('status', 'unknown').upper()}")
    print("=" * 60)

    if final_state.get("lgtm_summary"):
        print(final_state["lgtm_summary"])

    patches = final_state.get("suggested_patches", [])
    if patches:
        print(f"\nApplied Patches: {len(patches)}")
        for i, p in enumerate(patches, 1):
            print(f"  {i}. {p.get('file_path')} - {p.get('explanation')}")

    if final_state.get("status") == "failed":
        sys.exit(1)


def run_index(args):
    """Indexes and inspects AST symbols for a given directory."""
    path = Path(args.path).resolve()
    print(f"Indexing AST symbols in: {path}")
    parser = ASTParser()
    chunker = CodeChunker(parser=parser)
    chunks = chunker.chunk_directory(path)

    print(f"Found {len(chunks)} logical code chunks:")
    for chunk in chunks:
        print(f"  [{chunk.kind.upper()}] {chunk.name} ({chunk.file_path}:{chunk.start_line}-{chunk.end_line})")


def run_serve(args):
    """Starts the FastAPI webhook server."""
    import uvicorn
    print(f"Starting Webhook Server on {args.host}:{args.port}...")
    uvicorn.run("code_review_agent.github.webhook:app", host=args.host, port=args.port, reload=args.reload)


def main():
    parser = argparse.ArgumentParser(description="Self-Correcting Code Review & Architectural Audit Agent")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Audit command
    audit_parser = subparsers.add_parser("audit", help="Run audit and self-correction on target repo/files")
    audit_parser.add_argument("--path", "-p", default=".", help="Workspace path to audit (default: .)")
    audit_parser.add_argument("--files", "-f", nargs="*", default=None, help="Specific files to audit")
    audit_parser.add_argument("--auto-approve", action="store_true", help="Automatically approve structural changes")
    audit_parser.set_defaults(func=run_audit)

    # Index command
    index_parser = subparsers.add_parser("index", help="Index and display AST symbols and chunks")
    index_parser.add_argument("--path", "-p", default=".", help="Directory to inspect")
    index_parser.set_defaults(func=run_index)

    # Serve command
    serve_parser = subparsers.add_parser("serve", help="Run FastAPI GitHub webhook listener")
    serve_parser.add_argument("--host", default="0.0.0.0", help="Host address (default: 0.0.0.0)")
    serve_parser.add_argument("--port", type=int, default=8000, help="Port (default: 8000)")
    serve_parser.add_argument("--reload", action="store_true", help="Enable autoreload")
    serve_parser.set_defaults(func=run_serve)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
