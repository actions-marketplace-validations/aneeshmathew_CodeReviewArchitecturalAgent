from typing import TypedDict, List, Dict, Any, Optional


class AuditState(TypedDict, total=False):
    """The state schema representing repository audit and self-correction cycles.
    
    Conforms to Section 4 of code_review_architectural_agent.md.
    """
    # Repository context
    repo_url: str
    commit_sha: str
    workspace_path: str
    pr_number: Optional[int]
    changed_files: List[str]

    # Analysis results
    ast_summary: Dict[str, Any]
    static_errors: List[Dict[str, Any]]
    diff_summary: Optional[str]
    error_analysis: Optional[str]

    # Self-correction state
    suggested_patches: List[Dict[str, str]]  # list of {"file_path": str, "original": str, "patched": str, "diff": str}
    test_results: Dict[str, Any]
    retry_count: int

    # Human-in-the-loop & Final verdict
    is_structural_change: bool
    is_approved_by_human: bool
    lgtm_summary: Optional[str]
    status: str  # 'analyzing' | 'synthesizing' | 'testing' | 'awaiting_approval' | 'approved' | 'rejected' | 'success' | 'failed'
    comment_posted: bool
