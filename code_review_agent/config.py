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
    qdrant_path: str = Field(
        default=":memory:",
        description="Path to local Qdrant database or ':memory:' for transient store.",
    )
    qdrant_collection_name: str = Field(
        default="codebase_symbols",
        description="Collection name for indexed symbols.",
    )

    # GitHub Integration
    github_token: str = Field(
        default_factory=lambda: os.getenv("GITHUB_TOKEN", "")
    )
    github_webhook_secret: str = Field(
        default_factory=lambda: os.getenv("GITHUB_WEBHOOK_SECRET", "")
    )

    # Human-in-the-Loop controls
    require_human_approval_for_structural_changes: bool = Field(
        default=True,
        description="If True, pause before committing structural or breaking changes.",
    )


settings = Settings()
