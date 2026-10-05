from code_review_agent.llm import MultiModelCodeReviewer, CodeReviewer
from code_review_agent.analyzer.error_parser import DiagnosticError


def test_reviewer_provider_initialization():
    # OpenAI provider
    openai_rev = MultiModelCodeReviewer(provider="openai", api_key="sk-test-fake")
    assert openai_rev.provider == "openai"
    assert openai_rev.model == "gpt-4o-mini"

    # Anthropic provider
    claude_rev = MultiModelCodeReviewer(provider="anthropic", api_key="sk-ant-test-fake")
    assert claude_rev.provider == "anthropic"
    assert claude_rev.model == "claude-3-5-haiku-20241022"

    # Groq provider
    groq_rev = MultiModelCodeReviewer(provider="groq", api_key="gsk-test-fake")
    assert groq_rev.provider == "groq"
    assert groq_rev.model == "llama-3.3-70b-versatile"

    # Ollama / Custom provider
    ollama_rev = MultiModelCodeReviewer(provider="ollama", model="qwen2.5-coder:7b", base_url="http://localhost:11434/v1")
    assert ollama_rev.provider == "ollama"
    assert ollama_rev.model == "qwen2.5-coder:7b"
    assert ollama_rev.base_url == "http://localhost:11434/v1"


def test_reviewer_heuristic_fallback_when_no_key():
    reviewer = CodeReviewer(api_key=None)
    errors = [
        DiagnosticError(
            source_tool="ruff",
            file_path="sample.py",
            line_number=1,
            error_code="F401",
            message="'os' imported but unused",
            raw_trace=""
        )
    ]
    code = "import os\nprint('hello')\n"
    patch = reviewer.synthesize_fix("sample.py", code, errors, {})
    assert "removed unused import" in patch.patched_code
