"""Tests for the GitHub integration module."""

from unittest.mock import MagicMock, patch

import pytest

from pactwatch.github import (
    COMMENT_MARKER,
    GitHubIntegrationError,
    _find_existing_comment,
    post_pr_comment,
    set_commit_status,
)


class TestPostPrComment:
    @patch("pactwatch.github.get_client")
    def test_creates_new_comment(self, mock_get_client):
        """When no existing PactWatch comment exists, creates a new one."""
        mock_pr = MagicMock()
        mock_pr.get_issue_comments.return_value = []
        mock_repo = MagicMock()
        mock_repo.get_pull.return_value = mock_pr
        mock_client = MagicMock()
        mock_client.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_client

        post_pr_comment("token", "owner/repo", 1, "test body")

        mock_pr.create_issue_comment.assert_called_once_with("test body")

    @patch("pactwatch.github.get_client")
    def test_updates_existing_comment(self, mock_get_client):
        """When an existing PactWatch comment exists, edits it."""
        existing_comment = MagicMock()
        existing_comment.body = f"old report {COMMENT_MARKER}"
        mock_pr = MagicMock()
        mock_pr.get_issue_comments.return_value = [existing_comment]
        mock_repo = MagicMock()
        mock_repo.get_pull.return_value = mock_pr
        mock_client = MagicMock()
        mock_client.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_client

        post_pr_comment("token", "owner/repo", 1, "new body")

        existing_comment.edit.assert_called_once_with("new body")
        mock_pr.create_issue_comment.assert_not_called()

    @patch("pactwatch.github.get_client")
    def test_raises_on_repo_error(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.get_repo.side_effect = Exception("Not found")
        mock_get_client.return_value = mock_client

        with pytest.raises(GitHubIntegrationError, match="Failed to access"):
            post_pr_comment("token", "owner/repo", 1, "body")


class TestSetCommitStatus:
    @patch("pactwatch.github.get_client")
    def test_sets_status(self, mock_get_client):
        mock_commit = MagicMock()
        mock_repo = MagicMock()
        mock_repo.get_commit.return_value = mock_commit
        mock_client = MagicMock()
        mock_client.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_client

        set_commit_status("token", "owner/repo", "abc123", "success", "All good")

        mock_commit.create_status.assert_called_once_with(
            state="success",
            description="All good",
            context="pactwatch",
            target_url="",
        )

    @patch("pactwatch.github.get_client")
    def test_truncates_long_description(self, mock_get_client):
        mock_commit = MagicMock()
        mock_repo = MagicMock()
        mock_repo.get_commit.return_value = mock_commit
        mock_client = MagicMock()
        mock_client.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_client

        long_desc = "x" * 200
        set_commit_status("token", "owner/repo", "abc123", "failure", long_desc)

        call_args = mock_commit.create_status.call_args
        assert len(call_args.kwargs["description"]) <= 140


class TestFindExistingComment:
    def test_finds_comment_with_marker(self):
        comment = MagicMock()
        comment.body = f"Some text {COMMENT_MARKER} more text"
        mock_pr = MagicMock()
        mock_pr.get_issue_comments.return_value = [comment]

        result = _find_existing_comment(mock_pr)
        assert result == comment

    def test_returns_none_when_no_marker(self):
        comment = MagicMock()
        comment.body = "Just a regular comment"
        mock_pr = MagicMock()
        mock_pr.get_issue_comments.return_value = [comment]

        result = _find_existing_comment(mock_pr)
        assert result is None

    def test_returns_none_for_empty_comments(self):
        mock_pr = MagicMock()
        mock_pr.get_issue_comments.return_value = []

        result = _find_existing_comment(mock_pr)
        assert result is None
