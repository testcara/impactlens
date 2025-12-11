"""Jira API client for fetching issue data."""

import requests
import os

from impactlens.utils.logger import logger


class JiraClient:
    """Client for interacting with Jira REST API."""

    def __init__(self, jira_url=None, api_token=None):
        """
        Initialize Jira client with URL and API token.

        Args:
            jira_url: Jira server URL
            api_token: API token for authentication
        """
        self.jira_url = jira_url or os.getenv("JIRA_URL", "https://issues.redhat.com")
        self.api_token = api_token or os.getenv("JIRA_API_TOKEN")
        # Debug logging is disabled by default to avoid leaking sensitive info in CI logs

        self.headers = {"Accept": "application/json", "authorization": f"Bearer {self.api_token}"}

    def fetch_jira_data(self, jql_query, start_at=0, max_results=50, expand=None):
        """
        Fetch Jira Issue data with pagination support.

        Args:
            jql_query: JQL query string
            start_at: Starting index for pagination
            max_results: Maximum results per request
            expand: Optional fields to expand (e.g., 'changelog')

        Returns:
            JSON response from Jira API or None on error
        """
        url = f"{self.jira_url}/rest/api/2/search"

        params = {
            "jql": jql_query,
            "fields": "created,resolutiondate,status,issuetype,timeoriginalestimate,timetracking",
            "startAt": start_at,
            "maxResults": max_results,
        }

        if expand:
            params["expand"] = expand

        logger.debug("=== Jira API Request ===")
        logger.debug(f"URL: {url}")
        logger.debug(f"JQL Query: {jql_query}")
        logger.debug("Parameters:")
        for key, value in params.items():
            logger.debug(f"  {key}: {value}")
        logger.debug("=========================")

        try:
            response = requests.get(url, headers=self.headers, params=params)

            logger.debug(f"Response Status Code: {response.status_code}")
            logger.debug(f"Response URL: {response.url}")

            if not response.ok:
                logger.warning(f"Jira API request failed with status {response.status_code}")
                logger.debug(f"Error Response: {response.text}")

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

        Args:
            jql_query: JQL query string
            batch_size: Number of issues per request
            expand: Optional fields to expand

        Returns:
            List of all issues matching the query
        """
        initial_data = self.fetch_jira_data(jql_query, max_results=1)
        total_issues = initial_data.get("total", 0) if initial_data else 0

        logger.info(f"Total issues found: {total_issues}")

        all_issues = []
        if total_issues > 0:
            for start_at in range(0, total_issues, batch_size):
                logger.debug(
                    f"Fetching issues {start_at} to {min(start_at + batch_size, total_issues)}..."
                )
                data = self.fetch_jira_data(
                    jql_query, start_at=start_at, max_results=batch_size, expand=expand
                )
                if data and "issues" in data:
                    all_issues.extend(data["issues"])
                else:
                    logger.warning(f"Failed to fetch batch starting at {start_at}")
                    break

        return all_issues
