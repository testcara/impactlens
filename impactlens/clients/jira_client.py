"""Jira API client for fetching issue data."""

import requests
import os

from impactlens.utils.logger import logger


class JiraClient:
    """Client for interacting with Jira REST API."""

    def __init__(self, jira_url=None, api_token=None, email=None):
        """
        Initialize Jira client with URL and API token.

        Args:
            jira_url: Jira server URL
            api_token: API token for authentication
            email: Email for Atlassian Cloud Basic Auth (required for Atlassian Cloud)
        """
        self.jira_url = jira_url or os.getenv("JIRA_URL", "https://issues.redhat.com")
        self.api_token = api_token or os.getenv("JIRA_API_TOKEN")
        self.email = email or os.getenv("JIRA_EMAIL")
        # Debug logging is disabled by default to avoid leaking sensitive info in CI logs

        self.headers = {"Accept": "application/json"}

    def fetch_jira_data(self, jql_query, max_results=50, expand=None, next_page_token=None):
        """
        Fetch Jira Issue data with pagination support.

        Args:
            jql_query: JQL query string
            max_results: Maximum results per request (default 50, max 100)
            expand: Optional fields to expand (e.g., 'changelog')
            next_page_token: Token for fetching next page (for pagination)

        Returns:
            JSON response from Jira API or None on error
        """
        url = f"{self.jira_url}/rest/api/3/search/jql"

        # Prepare request body for POST request
        body = {
            "jql": jql_query,
            "fields": [
                "created",
                "resolutiondate",
                "status",
                "issuetype",
                "timeoriginalestimate",
                "timetracking",
            ],
            "maxResults": max_results,
        }

        if expand:
            # expand should be a comma-separated string, not an array
            if isinstance(expand, list):
                body["expand"] = ",".join(expand)
            else:
                body["expand"] = expand

        if next_page_token:
            body["nextPageToken"] = next_page_token

        # Add Content-Type header for JSON body
        headers = {**self.headers, "Content-Type": "application/json"}

        logger.debug("=== Jira API Request ===")
        logger.debug(f"URL: {url}")
        logger.debug(f"JQL Query: {jql_query}")
        logger.debug("Request Body:")
        for key, value in body.items():
            logger.debug(f"  {key}: {value}")
        logger.debug("=========================")

        try:
            # Use Basic Auth for Atlassian Cloud API
            auth = (self.email, self.api_token) if self.email else None
            response = requests.post(url, headers=headers, json=body, auth=auth)

            logger.debug(f"Response Status Code: {response.status_code}")
            logger.debug(f"Response URL: {response.url}")

            if not response.ok:
                logger.warning(f"Jira API request failed with status {response.status_code}")
                logger.warning(f"Error Response: {response.text}")
                logger.debug(f"Request Body: {body}")

            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching Jira data: {e}")
            logger.debug(f"Request failed with exception: {type(e).__name__}")
            if hasattr(e, "response") and e.response is not None:
                logger.debug(f"Response text: {e.response.text}")
            return None

    def fetch_all_issues(self, jql_query, batch_size=50, expand=None):
        """
        Fetch all issues matching a JQL query with automatic pagination.

        Note: Uses token-based pagination (nextPageToken) instead of offset-based (startAt).
        The API no longer returns a 'total' count in most cases.

        Args:
            jql_query: JQL query string
            batch_size: Number of issues per request (max 100)
            expand: Optional fields to expand

        Returns:
            List of all issues matching the query
        """
        all_issues = []
        next_page_token = None
        page_count = 0

        while True:
            page_count += 1
            logger.debug(f"Fetching page {page_count}...")

            data = self.fetch_jira_data(
                jql_query, max_results=batch_size, expand=expand, next_page_token=next_page_token
            )

            if not data:
                logger.warning(f"Failed to fetch page {page_count}")
                break

            if "issues" in data:
                issues_in_page = len(data["issues"])
                all_issues.extend(data["issues"])
                logger.debug(f"Fetched {issues_in_page} issues (total so far: {len(all_issues)})")

                # Check if there are more pages
                next_page_token = data.get("nextPageToken")
                if not next_page_token:
                    logger.info(f"Completed fetching all issues. Total: {len(all_issues)}")
                    break
            else:
                logger.warning("No 'issues' field in response")
                break

        return all_issues
