"""Unit tests for gitlabclient."""

import pytest

from platform_connectors import GitlabClient


def test_create_gitlab_client_with_empty_url() -> None:
    """GitLab client creation with invalid url must raise an exception."""
    with pytest.raises(ValueError, match="GitLab URL is invalid"):
        GitlabClient("", "token")


def test_create_gitlab_client_with_empty_token() -> None:
    """GitLab client creation with invalid token must raise an exception."""
    with pytest.raises(ValueError, match="GitLab token is invalid"):
        GitlabClient("http://test", "")
