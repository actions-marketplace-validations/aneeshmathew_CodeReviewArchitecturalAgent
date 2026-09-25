import logging
from typing import Any, Dict, List, Optional
from github import Github
from ..config import settings

logger = logging.getLogger(__name__)


class GitHubPRManager:
    """Manages PR status checks, inline comments, and PR branch creation via PyGithub."""

    def __init__(self, token: Optional[str] = None):
        self.token = token or settings.github_token
        self.client = Github(self.token) if self.token else None

    def post_pr_comment(self, repo_full_name: str, pr_number: int, comment_body: str) -> bool:
        """Posts a general review comment on the Pull Request."""
        if not self.client:
            logger.info(f"[Offline/No Token] PR Comment on {repo_full_name}#{pr_number}:\n{comment_body}")
            return True

        try:
            repo = self.client.get_repo(repo_full_name)
            pr = repo.get_pull(pr_number)
            pr.create_issue_comment(comment_body)
            return True
        except Exception as e:
            logger.error(f"Failed to post PR comment: {e}")
            return False

    def post_inline_comments(
        self,
        repo_full_name: str,
        pr_number: int,
        commit_sha: str,
        comments: List[Dict[str, Any]]
    ) -> bool:
        """Posts inline comments on specific lines of a PR diff."""
        if not self.client:
            for c in comments:
                logger.info(f"[Offline/No Token] Inline {c.get('path')}:{c.get('line')} -> {c.get('body')}")
            return True

        try:
            repo = self.client.get_repo(repo_full_name)
            pr = repo.get_pull(pr_number)
            commit = repo.get_commit(commit_sha)

            for c in comments:
                pr.create_review_comment(
                    body=c["body"],
                    commit=commit,
                    path=c["path"],
                    line=c["line"]
                )
            return True
        except Exception as e:
            logger.error(f"Failed to create inline review comments: {e}")
            return False

    def create_or_update_pr(
        self,
        repo_full_name: str,
        base_branch: str,
        head_branch: str,
        title: str,
        body: str
    ) -> Optional[int]:
        """Creates an automated pull request with self-corrected changes."""
        if not self.client:
            logger.info(f"[Offline/No Token] Would create PR {title} from {head_branch} into {base_branch}")
            return 1

        try:
            repo = self.client.get_repo(repo_full_name)
            pr = repo.create_pull(
                title=title,
                body=body,
                base=base_branch,
                head=head_branch
            )
            return pr.number
        except Exception as e:
            logger.error(f"Failed to create pull request: {e}")
            return None
