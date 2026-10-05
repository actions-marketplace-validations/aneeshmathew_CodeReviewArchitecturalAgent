import os
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseModel):
    """Application settings and configuration."""

    # LLM & Multi-Model BYOK (Bring Your Own Key) Configuration
    llm_provider: str = Field(
        default_factory=lambda: os.getenv("LLM_PROVIDER", "gemini").lower(),
        description="LLM provider: 'gemini', 'openai', 'anthropic', 'groq', 'custom', or 'ollama'.",
    )
    llm_model: str = Field(
        default_factory=lambda: os.getenv("LLM_MODEL", ""),
        description="Model name (e.g., 'gpt-4o-mini', 'claude-3-5-haiku-20241022', 'gemini-2.5-flash').",
    )
    llm_api_key: str = Field(
        default_factory=lambda: os.getenv("LLM_API_KEY", ""),
        description="Generic API key for selected LLM provider.",
    )
    llm_base_url: str = Field(
        default_factory=lambda: os.getenv("LLM_BASE_URL", os.getenv("OPENAI_BASE_URL", "")),
        description="Custom base URL for OpenAI-compatible or local model endpoints.",
    )

    # Provider-Specific API Keys & Models
    gemini_api_key: str = Field(
        default_factory=lambda: os.getenv("GEMINI_API_KEY", "")
    )
    gemini_model: str = Field(
        default="gemini-3.5-flash-lite",
        description="Default Gemini model.",
    )
    gemini_embedding_model: str = Field(
        default="gemini-embedding-001",
        description="Embedding model for code vectorization.",
    )
    openai_api_key: str = Field(
        default_factory=lambda: os.getenv("OPENAI_API_KEY", "")
    )
    anthropic_api_key: str = Field(
        default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", "")
    )
    groq_api_key: str = Field(
        default_factory=lambda: os.getenv("GROQ_API_KEY", "")
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

    # Pinecone Vector Store
    pinecone_api_key: str = Field(
        default_factory=lambda: os.getenv("PINECONE_API_KEY", ""),
        description="Pinecone API key for serverless vector index.",
    )
    pinecone_index_name: str = Field(
        default_factory=lambda: os.getenv("PINECONE_INDEX_NAME", "codebase-symbols"),
        description="Pinecone index name (lowercase alphanumeric and hyphens only).",
    )
    pinecone_cloud: str = Field(
        default_factory=lambda: os.getenv("PINECONE_CLOUD", "aws"),
        description="Pinecone serverless cloud provider (e.g., 'aws').",
    )
    pinecone_region: str = Field(
        default_factory=lambda: os.getenv("PINECONE_REGION", "us-east-1"),
        description="Pinecone serverless region (e.g., 'us-east-1').",
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
