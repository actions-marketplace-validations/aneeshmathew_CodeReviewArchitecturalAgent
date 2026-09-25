import tempfile
from pathlib import Path
from code_review_agent.sandbox.executor import SandboxExecutor


def test_sandbox_run_command():
    sandbox = SandboxExecutor()
    res = sandbox.run_command(["python3", "-c", "print('sandbox_ok')"])
    assert res.success
    assert "sandbox_ok" in res.stdout


def test_sandbox_snapshot_and_rollback():
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write("ORIGINAL_CONTENT")
        path = Path(f.name)

    sandbox = SandboxExecutor()
    try:
        # Save snapshot and apply new patch
        sandbox.snapshot_file(path)
        sandbox.apply_patch(path, "MODIFIED_PATCH_CONTENT")
        assert path.read_text() == "MODIFIED_PATCH_CONTENT"

        # Rollback
        sandbox.rollback()
        assert path.read_text() == "ORIGINAL_CONTENT"
    finally:
        path.unlink(missing_ok=True)
