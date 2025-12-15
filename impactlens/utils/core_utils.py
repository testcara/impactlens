"""Utility functions for Jira data analysis."""

import csv
import re
from datetime import datetime


def calculate_days_between(start_date, end_date, inclusive=True):
    """
    Calculate the number of days between two dates.

    Args:
        start_date: Start date string (YYYY-MM-DD)
        end_date: End date string (YYYY-MM-DD)
        inclusive: If True, includes both start and end dates (adds 1 to result)

    Returns:
        Number of days or None if calculation fails
    """
    if not start_date or not end_date:
        return None

    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        days = (end - start).days
        if inclusive:
            days += 1
        return days if days >= 0 else None
    except (ValueError, TypeError):
        return None


def calculate_daily_throughput(start_date, end_date, item_count):
    """
    Calculate daily throughput based on date range and item count.

    Args:
        start_date: Start date string (YYYY-MM-DD)
        end_date: End date string (YYYY-MM-DD)
        item_count: Number of items to calculate throughput for

    Returns:
        Daily throughput (items per day) or None if calculation fails
    """
    days = calculate_days_between(start_date, end_date, inclusive=True)
    if days and days > 0:
        return item_count / days
    return None


def convert_date_to_jql(date_str):
    """
    Convert YYYY-MM-DD format date to Jira JQL relative time expression.

    Args:
        date_str: Date string in YYYY-MM-DD format

    Returns:
        JQL time expression (e.g., "-300d" for 300 days ago)
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


def parse_datetime(datetime_str):
    """
    Parse Jira datetime string to datetime object.

    Args:
        datetime_str: Jira datetime string

    Returns:
        datetime object or None on error
    """
    if not datetime_str:
        return None

    try:
        return datetime.strptime(datetime_str, "%Y-%m-%dT%H:%M:%S.%f%z")
    except ValueError:
        try:
            return datetime.strptime(datetime_str, "%Y-%m-%dT%H:%M:%S%z")
        except ValueError:
            return None


def calculate_state_durations(issue):
    """
    Calculate time spent in each state for an issue.

    Args:
        issue: Jira issue dict with changelog

    Returns:
        Dict mapping state names to statistics (total_seconds, count)
    """
    state_stats = {}

    changelog = issue.get("changelog", {})
    histories = changelog.get("histories", [])

    created_str = issue["fields"].get("created")
    current_status = issue["fields"].get("status", {}).get("name", "Unknown")
    resolution_str = issue["fields"].get("resolutiondate")

    if not created_str:
        return {}

    created_date = parse_datetime(created_str)
    if not created_date:
        return {}

    # Build status transition history
    status_transitions = []

    for history in histories:
        history_created = history.get("created")
        if not history_created:
            continue

        transition_date = parse_datetime(history_created)
        if not transition_date:
            continue

        for item in history.get("items", []):
            if item.get("field") == "status":
                from_status = item.get("fromString")
                to_status = item.get("toString")
                status_transitions.append(
                    {"date": transition_date, "from": from_status, "to": to_status}
                )

    # Sort by time
    status_transitions.sort(key=lambda x: x["date"])

    # Determine initial status
    if status_transitions:
        initial_status = status_transitions[0]["from"]
    else:
        initial_status = current_status

    # Calculate time spent in each state
    current_state = initial_status
    current_state_start = created_date

    # Initialize first state
    if current_state:
        if current_state not in state_stats:
            state_stats[current_state] = {"total_seconds": 0, "count": 0}
        state_stats[current_state]["count"] += 1

    # Process all transitions
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
            end_date = parse_datetime(resolution_str)
            if not end_date:
                end_date = datetime.now(current_state_start.tzinfo)
        else:
            end_date = datetime.now(current_state_start.tzinfo)

        duration = (end_date - current_state_start).total_seconds()
        state_stats[current_state]["total_seconds"] += duration

    return state_stats


def build_jql_query(project_key, start_date=None, end_date=None, status=None, assignee=None):
    """
    Build a JQL query string from parameters.

    Args:
        project_key: Jira project key
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        status: Issue status filter
        assignee: Assignee filter

    Returns:
        JQL query string
    """
    jql_parts = [f'project = "{project_key}"']

    if assignee:
        jql_parts.append(f'assignee = "{assignee}"')

    if start_date or end_date:
        if start_date:
            start_jql = convert_date_to_jql(start_date)
            jql_parts.append(f"resolved >= {start_jql}")

        if end_date:
            end_jql = convert_date_to_jql(end_date)
            jql_parts.append(f"resolved <= {end_jql}")
    else:
        if status:
            jql_parts.append(f'status = "{status}"')

    return " AND ".join(jql_parts)


def read_tsv_report(filepath):
    """
    Read TSV/CSV report file and return as list of rows.

    Args:
        filepath: Path to TSV or CSV file

    Returns:
        List of lists (rows)
    """
    rows = []

    # Detect delimiter
    delimiter = "\t" if filepath.endswith(".tsv") else ","

    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter=delimiter)
        for row in reader:
            rows.append(row)

    return rows


def normalize_username(username):
    """
    Normalize username by removing common prefixes/suffixes:
    - Remove @redhat.com, @gmail.com, etc.
    - Remove rh-ee- prefix
    - Remove -1, -2, etc. suffix

    Args:
        username: Username string to normalize

    Returns:
        Normalized username string
    """
    # Remove email domain
    username = username.split("@")[0]
    # Remove rh-ee- prefix
    if username.startswith("rh-ee-"):
        username = username[6:]  # len("rh-ee-") = 6
    # Remove -1, -2, etc. suffix
    username = re.sub(r"-\d+$", "", username)
    return username


def convert_markdown_to_plain_text(text):
    """
    Convert Markdown formatting to plain text for Google Sheets.

    Args:
        text: Text with Markdown formatting

    Returns:
        Plain text with Markdown removed
    """
    # Remove bold: **text** -> text
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)

    # Remove italic: *text* or _text_ -> text
    # For asterisk italics
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    # For underscore italics - only match if surrounded by whitespace or boundaries
    # to avoid matching underscores in filenames like combined_pr_report_20251215.tsv
    text = re.sub(r"(?<!\w)_([^_\s]+?)_(?!\w)", r"\1", text)

    # Remove headers: ### text -> text
    text = re.sub(r"^#{1,6}\s+", "", text)

    # Remove inline code: `text` -> text
    text = re.sub(r"`(.+?)`", r"\1", text)

    # Remove links: [text](url) -> text
    text = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", text)

    return text


def read_ai_analysis_report(filepath):
    """
    Read AI analysis report (plain text with Markdown) for Google Sheets upload.

    Converts to single-column format with Markdown formatting removed.

    Args:
        filepath: Path to AI analysis report file

    Returns:
        List of rows, each row is a list with single cell containing the line text
    """
    rows = []

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            # Remove trailing newline
            line = line.rstrip("\n\r")

            # Convert Markdown to plain text
            plain_line = convert_markdown_to_plain_text(line)

            # Each line becomes a single-cell row
            rows.append([plain_line])

    return rows
