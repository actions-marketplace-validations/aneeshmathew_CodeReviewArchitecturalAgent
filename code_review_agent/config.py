import os
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseModel):
    """Application settings and configuration."""

    # Gemini Free Tier Configuration
    gemini_api_key: str = Field(
        default_factory=lambda: os.getenv("GEMINI_API_KEY", "")
    )
    gemini_model: str = Field(
        default="gemini-3.5-flash-lite",
        description="Default LLM model, utilizing Google Gemini Free Tier.",
    )
    gemini_embedding_model: str = Field(
        default="gemini-embedding-001",
        description="Embedding model for code vectorization.",
    )

    # Agent Loop Controls
    max_retries: int = Field(
        default=3,
        description="Maximum self-correction loop iterations before failing/escalating.",
    )
    sandbox_timeout_seconds: int = Field(
        default=30,
        description="Timeout for running tests and analyzers inside sandbox.",
    )

    # Qdrant Vector Store
    qdrant_url: str = Field(
        default_factory=lambda: os.getenv("QDRANT_URL", ""),
        description="Remote Qdrant Cloud cluster URL.",
    )
    qdrant_api_key: str = Field(
        default_factory=lambda: os.getenv("QDRANT_API_KEY", ""),
        description="Qdrant Cloud API key.",
    )
    qdrant_path: str = Field(
        default=":memory:",
        description="Path to local Qdrant database or ':memory:' for transient store when URL is not set.",
    )
    qdrant_collection_name: str = Field(
        default="codebase_symbols",
        description="Collection name for indexed symbols.",
    )

    # GitHub Integration
    github_token: str = Field(
        default_factory=lambda: (
            os.getenv("GITHUB_TOKEN", "").strip()
            or _resolve_gh_cli_token()
        )
    )
    github_webhook_secret: str = Field(
        default_factory=lambda: os.getenv("GITHUB_WEBHOOK_SECRET", "")
    )

    # Human-in-the-Loop controls
    require_human_approval_for_structural_changes: bool = Field(
        default=True,
        description="If True, pause before committing structural or breaking changes.",
    )


def _resolve_gh_cli_token() -> str:
    """Attempts to auto-resolve token from system `gh` CLI if user logged in via `gh auth login`."""
    try:
        import subprocess
        res = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, timeout=2)
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip()
    except Exception:
        pass
    return ""


settings = Settings()
