"""Tests for Jira client."""

import requests
from unittest.mock import Mock, patch
from impactlens.clients.jira_client import JiraClient


class TestJiraClient:
    """Test JiraClient class."""

    def test_init_with_defaults(self):
        """Test initialization with default values."""
        with patch.dict(
            "os.environ", {"JIRA_URL": "https://test.jira.com", "JIRA_API_TOKEN": "test-token"}
        ):
            client = JiraClient()
            assert client.jira_url == "https://test.jira.com"
            assert client.api_token == "test-token"

    def test_init_with_params(self):
        """Test initialization with explicit parameters."""
        client = JiraClient(jira_url="https://custom.jira.com", api_token="custom-token")
        assert client.jira_url == "https://custom.jira.com"
        assert client.api_token == "custom-token"

    def test_init_with_email(self):
        """Test initialization with email for Basic Auth."""
        client = JiraClient(
            jira_url="https://custom.jira.com",
            api_token="custom-token",
            email="user@example.com",
        )
        assert client.jira_url == "https://custom.jira.com"
        assert client.api_token == "custom-token"
        assert client.email == "user@example.com"

    @patch("impactlens.clients.jira_client.requests.post")
    def test_fetch_jira_data_success(self, mock_post):
        """Test successful Jira data fetch."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {"total": 10, "issues": []}
        mock_post.return_value = mock_response

        client = JiraClient(jira_url="https://test.jira.com", api_token="test-token")
        result = client.fetch_jira_data('project = "TEST"')

        assert result is not None
        assert result["total"] == 10
        mock_post.assert_called_once()

    @patch("impactlens.clients.jira_client.requests.post")
    def test_fetch_jira_data_error(self, mock_post):
        """Test Jira data fetch with error."""
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 403
        mock_response.text = "Forbidden"
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("HTTP Error")
        mock_post.return_value = mock_response

        client = JiraClient(jira_url="https://test.jira.com", api_token="test-token")
        result = client.fetch_jira_data('project = "TEST"')

        assert result is None

    @patch("impactlens.clients.jira_client.requests.post")
    def test_fetch_all_issues(self, mock_post):
        """Test fetching all issues with token-based pagination."""
        # First page with nextPageToken
        mock_response1 = Mock()
        mock_response1.ok = True
        mock_response1.status_code = 200
        mock_response1.json.return_value = {
            "issues": [{"key": "TEST-1"}],
            "nextPageToken": "token123",
        }

        # Second page without nextPageToken (last page)
        mock_response2 = Mock()
        mock_response2.ok = True
        mock_response2.status_code = 200
        mock_response2.json.return_value = {
            "issues": [{"key": "TEST-2"}],
        }

        mock_post.side_effect = [mock_response1, mock_response2]

        client = JiraClient(jira_url="https://test.jira.com", api_token="test-token")
        result = client.fetch_all_issues('project = "TEST"', batch_size=50)

        assert len(result) == 2
        assert result[0]["key"] == "TEST-1"
        assert result[1]["key"] == "TEST-2"
        assert mock_post.call_count == 2
