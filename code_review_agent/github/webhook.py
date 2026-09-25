import hashlib
import hmac
import logging
from typing import Any, Dict
from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request
from ..config import settings
from ..graph.workflow import create_audit_graph
from ..state import AuditState

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Self-Correcting Code Review & Architectural Audit Agent",
    description="Automated GitHub webhook receiver and LangGraph self-correction runner powered by Gemini 3.5 Flash-Lite.",
    version="0.1.0"
)


def verify_github_signature(payload_bytes: bytes, signature_header: str | None, secret: str) -> bool:
    """Validates the GitHub HMAC-SHA256 signature."""
    if not secret:
        return True
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected_hash = hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()
    incoming_hash = signature_header.split("sha256=")[-1]
    return hmac.compare_digest(expected_hash, incoming_hash)


def run_audit_workflow(state: AuditState):
    """Executes the LangGraph audit cycle asynchronously."""
    try:
        graph = create_audit_graph()
        result = graph.invoke(state)
        logger.info(f"Audit completed with status: {result.get('status')}")
    except Exception as e:
        logger.error(f"Error executing audit workflow: {e}")


@app.get("/health")
async def health_check():
    """Service health probe."""
    return {
        "status": "healthy",
        "model": settings.gemini_model,
        "max_retries": settings.max_retries,
    }


@app.post("/webhook")
async def handle_github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_github_event: str = Header(None),
    x_hub_signature_256: str = Header(None)
):
    """Processes GitHub webhook events (pull_request, push)."""
    payload_bytes = await request.body()

    if settings.github_webhook_secret:
        if not verify_github_signature(payload_bytes, x_hub_signature_256, settings.github_webhook_secret):
            raise HTTPException(status_code=401, detail="Invalid HMAC signature.")

    try:
        payload: Dict[str, Any] = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body.")

    if x_github_event == "ping":
        return {"msg": "pong"}

    initial_state: AuditState = {
        "repo_url": "",
        "commit_sha": "",
        "workspace_path": ".",
        "changed_files": [],
        "retry_count": 0,
        "is_approved_by_human": False,
        "status": "inbound_event",
    }

    if x_github_event == "pull_request":
        action = payload.get("action")
        pr_data = payload.get("pull_request", {})
        repo_data = payload.get("repository", {})

        if action in ("opened", "synchronize", "reopened"):
            initial_state["repo_url"] = repo_data.get("html_url", "")
            initial_state["commit_sha"] = pr_data.get("head", {}).get("sha", "")
            initial_state["pr_number"] = pr_data.get("number")
            
            # Queue the background LangGraph execution
            background_tasks.add_task(run_audit_workflow, initial_state)

            return {
                "message": f"PR #{initial_state['pr_number']} accepted for self-correcting audit.",
                "action": action,
                "head_sha": initial_state["commit_sha"],
            }

    return {"message": f"Event '{x_github_event}' acknowledged, no action needed."}
