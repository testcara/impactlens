"""
Jira Metrics Calculator

Core business logic for fetching Jira data and calculating metrics.
Extracted from cli/get_jira_metrics.py
"""

import os
import json
from datetime import datetime
from pathlib import Path

from impactlens.clients.jira_client import JiraClient
from impactlens.utils.logger import logger
from impactlens.utils.report_utils import normalize_username
from impactlens.utils.workflow_utils import load_members_emails


class JiraMetricsCalculator:
    """
    Calculator for Jira issue metrics including closure times,
    state durations, and velocity.
    """

    def __init__(self, jira_url=None, jira_token=None, jira_email=None, project_key=None):
        """
        Initialize the Jira metrics calculator.

        Args:
            jira_url: Jira instance URL (default: from JIRA_URL env var)
            jira_token: Jira API token (default: from JIRA_API_TOKEN env var)
            jira_email: Jira email for Basic Auth (default: from JIRA_EMAIL env var)
            project_key: Project key (default: from JIRA_PROJECT_KEY env var)
        """
        self.project_key = project_key or os.getenv("JIRA_PROJECT_KEY", "Konflux UI")

        # Use JiraClient for all API interactions
        self.jira_client = JiraClient(jira_url=jira_url, api_token=jira_token, email=jira_email)

    def calculate_state_durations(self, issue):
        """
        Calculate the time spent in each state for an issue and the number of occurrences.

        Args:
            issue: Jira issue dict with changelog data

        Returns:
            Dictionary containing total time (seconds) and occurrence count for each state
        """
        state_stats = {}

        changelog = issue.get("changelog", {})
        histories = changelog.get("histories", [])

        created_str = issue["fields"].get("created")
        current_status = issue["fields"].get("status", {}).get("name", "Unknown")
        resolution_str = issue["fields"].get("resolutiondate")

        if not created_str:
            return {}

        try:
            created_date = datetime.strptime(created_str, "%Y-%m-%dT%H:%M:%S.%f%z")
        except ValueError:
            try:
                created_date = datetime.strptime(created_str, "%Y-%m-%dT%H:%M:%S%z")
            except ValueError:
                return {}

        # Build status transition history
        status_transitions = []

        for history in histories:
            history_created = history.get("created")
            if not history_created:
                continue

            try:
                transition_date = datetime.strptime(history_created, "%Y-%m-%dT%H:%M:%S.%f%z")
            except ValueError:
                try:
                    transition_date = datetime.strptime(history_created, "%Y-%m-%dT%H:%M:%S%z")
                except ValueError:
                    continue

            for item in history.get("items", []):
                if item.get("field") == "status":
                    from_status = item.get("fromString")
                    to_status = item.get("toString")
                    status_transitions.append(
                        {"date": transition_date, "from": from_status, "to": to_status}
                    )

        status_transitions.sort(key=lambda x: x["date"])

        # Determine initial status
        if status_transitions:
            initial_status = status_transitions[0]["from"]
        else:
            initial_status = current_status

        # Calculate time spent in each state
        current_state = initial_status
        current_state_start = created_date

        if current_state:
            if current_state not in state_stats:
                state_stats[current_state] = {"total_seconds": 0, "count": 0}
            state_stats[current_state]["count"] += 1

        for transition in status_transitions:
            if current_state:
                duration = (transition["date"] - current_state_start).total_seconds()
                state_stats[current_state]["total_seconds"] += duration

            current_state = transition["to"]
            current_state_start = transition["date"]

            if current_state not in state_stats:
                state_stats[current_state] = {"total_seconds": 0, "count": 0}
            state_stats[current_state]["count"] += 1

        # Calculate time for last state
        if current_state:
            if resolution_str:
                try:
                    end_date = datetime.strptime(resolution_str, "%Y-%m-%dT%H:%M:%S.%f%z")
                except ValueError:
                    try:
                        end_date = datetime.strptime(resolution_str, "%Y-%m-%dT%H:%M:%S%z")
                    except ValueError:
                        end_date = datetime.now(current_state_start.tzinfo)
            else:
                end_date = datetime.now(current_state_start.tzinfo)

            duration = (end_date - current_state_start).total_seconds()
            state_stats[current_state]["total_seconds"] += duration

        return state_stats

    def convert_date_to_jql(self, date_str):
        """
        Convert YYYY-MM-DD format date to Jira JQL relative time expression.

        Args:
            date_str: Date string in YYYY-MM-DD format

        Returns:
            JQL time expression (e.g., "-300d")
        """
        if not date_str:
            return None

        try:
            input_date = datetime.strptime(date_str, "%Y-%m-%d")
            today = datetime.now()
            days_diff = (today - input_date).days

            if days_diff == 0:
                return "startOfDay()"
            elif days_diff > 0:
                return f'"-{days_diff}d"'
            else:
                return f'"{abs(days_diff)}d"'
        except ValueError:
            return f'"{date_str}"'

    def build_jql_query(
        self,
        project_key=None,
        assignee=None,
        members_file=None,
        start_date=None,
        end_date=None,
        status=None,
    ):
        """
        Build JQL query based on filters.

        Args:
            project_key: Jira project key
            assignee: Single assignee to filter by
            members_file: Path to team members config file
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            status: Issue status

        Returns:
            Tuple of (jql_query, members_list)
        """
        project_key = project_key or self.project_key
        jql_parts = [f'project = "{project_key}"']

        members = []

        # Add assignee filter
        if assignee:
            jql_parts.append(f'assignee = "{assignee}"')
            logger.debug(f"Filtering by assignee: {assignee}")
        elif members_file:
            # Load team members from config file using YAML parser
            try:
                # Just get emails list
                members = load_members_emails(Path(members_file))

                if members:
                    assignee_conditions = " OR ".join(
                        [f'assignee = "{member}"' for member in members]
                    )
                    jql_parts.append(f"({assignee_conditions})")
                    logger.info(f"Limiting to team members from config: {len(members)} members")
                    logger.debug(f"Team members: {', '.join(members)}")
                else:
                    logger.warning("No team members found in config file")
            except Exception as e:
                logger.warning(f"Error reading team members file: {e}")

        # Add date filters
        if start_date or end_date:
            if start_date:
                start_jql = self.convert_date_to_jql(start_date)
                jql_parts.append(f"resolved >= {start_jql}")
                logger.debug(f"Start date {start_date} converted to: {start_jql}")

            if end_date:
                end_jql = self.convert_date_to_jql(end_date)
                jql_parts.append(f"resolved <= {end_jql}")
                logger.debug(f"End date {end_date} converted to: {end_jql}")
        else:
            # Only use status when no date filter
            if status:
                jql_parts.append(f'status = "{status}"')

        return " AND ".join(jql_parts), members

    def fetch_all_issues(self, jql_query, batch_size=50):
        """
        Fetch all issues matching JQL query with pagination.

        Uses JiraClient's token-based pagination (API v3).

        Args:
            jql_query: JQL query string
            batch_size: Results per page

        Returns:
            List of all issues with changelog data
        """
        logger.info(f"Fetching all issues for JQL: {jql_query}")

        # Use JiraClient's fetch_all_issues with changelog expansion
        all_issues = self.jira_client.fetch_all_issues(
            jql_query, batch_size=batch_size, expand="changelog"
        )

        logger.info(f"Total issues fetched for analysis: {len(all_issues)}")
        return all_issues

    def calculate_metrics(self, issues):
        """
        Calculate comprehensive metrics from issues.

        Args:
            issues: List of Jira issues

        Returns:
            Dictionary containing all calculated metrics
        """
        if not issues:
            return self._empty_metrics()

        closing_times = []
        created_dates = []
        resolution_dates = []
        issue_types = {}

        # Calculate basic metrics
        for issue in issues:
            try:
                created_str = issue["fields"].get("created")
                resolution_str = issue["fields"].get("resolutiondate")
                issue_type = issue["fields"].get("issuetype", {}).get("name", "Unknown")

                if issue_type not in issue_types:
                    issue_types[issue_type] = 0
                issue_types[issue_type] += 1

                if created_str and resolution_str:
                    created_date = datetime.strptime(created_str, "%Y-%m-%dT%H:%M:%S.%f%z")
                    resolution_date = datetime.strptime(resolution_str, "%Y-%m-%dT%H:%M:%S.%f%z")

                    created_dates.append(created_date)
                    resolution_dates.append(resolution_date)

                    time_diff = (resolution_date - created_date).total_seconds()
                    closing_times.append(time_diff)
            except Exception as e:
                logger.warning(f"Error processing issue {issue.get('key', 'unknown')}: {e}")

        # Calculate state durations
        all_states_aggregated = {}
        for issue in issues:
            state_stats = self.calculate_state_durations(issue)

            for state, stats in state_stats.items():
                if state not in all_states_aggregated:
                    all_states_aggregated[state] = {
                        "total_seconds": 0,
                        "total_count": 0,
                        "issue_count": 0,
                    }
                all_states_aggregated[state]["total_seconds"] += stats["total_seconds"]
                all_states_aggregated[state]["total_count"] += stats["count"]
                all_states_aggregated[state]["issue_count"] += 1

        return {
            "total_issues": len(issues),
            "issue_types": issue_types,
            "closing_times": closing_times,
            "created_dates": created_dates,
            "resolution_dates": resolution_dates,
            "state_stats": all_states_aggregated,
        }

    def _empty_metrics(self):
        """Return empty metrics structure."""
        return {
            "total_issues": 0,
            "issue_types": {},
            "closing_times": [],
            "created_dates": [],
            "resolution_dates": [],
            "state_stats": {},
        }

    def calculate_velocity(self, project_key, start_date=None, end_date=None, batch_size=50):
        """
        Calculate velocity based on story points.

        Args:
            project_key: Jira project key
            start_date: Start date filter
            end_date: End date filter
            batch_size: Batch size for pagination

        Returns:
            Dictionary with velocity statistics
        """
        jql_stories_parts = [f'project = "{project_key}"', "issuetype = Story"]

        if start_date:
            start_jql = self.convert_date_to_jql(start_date)
            jql_stories_parts.append(f"resolved >= {start_jql}")

        if end_date:
            end_jql = self.convert_date_to_jql(end_date)
            jql_stories_parts.append(f"resolved <= {end_jql}")

        jql_stories = " AND ".join(jql_stories_parts)

        logger.debug(f"Story query JQL: {jql_stories}")

        # Use JiraClient's fetch_all_issues for token-based pagination
        all_stories = self.jira_client.fetch_all_issues(
            jql_stories, batch_size=batch_size, expand="changelog"
        )

        total_stories = len(all_stories)

        if total_stories == 0:
            return {
                "total_stories": 0,
                "stories_with_points": 0,
                "total_story_points": 0,
                "avg_points_per_story": 0,
            }

        total_story_points = 0
        stories_with_points = 0

        for story in all_stories:
            story_points = story["fields"].get("customfield_12310243")
            if story_points:
                total_story_points += float(story_points)
                stories_with_points += 1

        return {
            "total_stories": total_stories,
            "stories_with_points": stories_with_points,
            "total_story_points": total_story_points,
            "avg_points_per_story": (
                total_story_points / stories_with_points if stories_with_points > 0 else 0
            ),
        }
