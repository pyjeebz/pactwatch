"""GitHub API integration -- PR comments and commit status checks."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from github import Github
    from github.PullRequest import PullRequest

COMMENT_MARKER = "<!-- breakwatch-report -->"


class GitHubIntegrationError(Exception):
    """Raised when GitHub API operations fail."""


def get_client(token: str) -> "Github":
    """Create a GitHub API client.

    Args:
        token: GitHub personal access token or GITHUB_TOKEN.

    Returns:
        An authenticated PyGithub client.

    Raises:
        GitHubIntegrationError: If pygithub is not installed.
    """
    try:
        from github import Github
    except ImportError:
        raise GitHubIntegrationError(
            "pygithub is not installed. "
            "Install it with: pip install breakwatch[github]"
        )
    return Github(token)


def post_pr_comment(
    token: str,
    repo_name: str,
    pr_number: int,
    body: str,
) -> None:
    """Create or update a Breakwatch comment on a pull request.

    Uses an upsert pattern: searches for an existing comment containing
    the Breakwatch marker and edits it. If no existing comment is found,
    creates a new one.

    Args:
        token: GitHub token with PR comment permissions.
        repo_name: Full repo name (e.g. 'pyjeebz/breakwatch').
        pr_number: Pull request number.
        body: The markdown body to post.
    """
    client = get_client(token)

    try:
        repo = client.get_repo(repo_name)
        pr = repo.get_pull(pr_number)
    except Exception as exc:
        raise GitHubIntegrationError(
            f"Failed to access PR #{pr_number} in {repo_name}: {exc}"
        ) from exc

    # Search for existing Breakwatch comment (upsert)
    existing = _find_existing_comment(pr)
    if existing:
        try:
            existing.edit(body)
        except Exception as exc:
            raise GitHubIntegrationError(
                f"Failed to update comment: {exc}"
            ) from exc
    else:
        try:
            pr.create_issue_comment(body)
        except Exception as exc:
            raise GitHubIntegrationError(
                f"Failed to create comment: {exc}"
            ) from exc


def set_commit_status(
    token: str,
    repo_name: str,
    sha: str,
    state: str,
    description: str,
    target_url: str | None = None,
) -> None:
    """Set a commit status check on a specific commit.

    Args:
        token: GitHub token.
        repo_name: Full repo name.
        sha: The commit SHA to set status on.
        state: One of 'success', 'failure', 'pending', 'error'.
        description: Short description for the status check.
        target_url: Optional URL linking to more details.
    """
    client = get_client(token)

    try:
        repo = client.get_repo(repo_name)
        commit = repo.get_commit(sha)
        commit.create_status(
            state=state,
            description=description[:140],  # GitHub limits to 140 chars
            context="breakwatch",
            target_url=target_url or "",
        )
    except Exception as exc:
        raise GitHubIntegrationError(
            f"Failed to set commit status: {exc}"
        ) from exc


def _find_existing_comment(pr: "PullRequest"):
    """Find an existing Breakwatch comment on a PR."""
    for comment in pr.get_issue_comments():
        if COMMENT_MARKER in (comment.body or ""):
            return comment
    return None
