import shutil
import tempfile
from pathlib import Path
from code_review_agent.graph.workflow import create_audit_graph
from code_review_agent.state import AuditState


def test_self_correcting_audit_workflow():
    # Setup isolated test directory with buggy sample
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        benchmark_dir = Path(__file__).parent.parent / "benchmark_sample"

        shutil.copy(benchmark_dir / "buggy_math.py", temp_path / "buggy_math.py")
        shutil.copy(benchmark_dir / "test_buggy_math.py", temp_path / "test_buggy_math.py")

        initial_state: AuditState = {
            "repo_url": "https://github.com/example/repo",
            "commit_sha": "abc1234",
            "workspace_path": str(temp_path),
            "changed_files": ["buggy_math.py"],
            "retry_count": 0,
            "is_approved_by_human": True,
            "status": "started",
        }

        graph = create_audit_graph()
        final_state = graph.invoke(initial_state)

        # The loop should execute self-correction
        assert final_state["status"] in ("complete", "success")
        assert len(final_state.get("suggested_patches", [])) >= 1
        assert final_state.get("comment_posted") is True
