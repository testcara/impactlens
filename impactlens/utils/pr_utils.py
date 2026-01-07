"""
PR-related utility functions.

This module provides shared utilities for PR analysis across different GitHub clients.
"""

from typing import Dict, List, Any


def extract_ai_info_from_commits(commits: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Extract AI assistance information from commit messages.

    This function analyzes commit messages to detect AI tool usage markers.
    Supports multiple patterns for Claude and Cursor AI tools.

    Args:
        commits: List of commit dictionaries. Each commit should have:
                 - For GraphQL: commit["commit"]["message"]
                 - For REST API: commit["commit"]["message"]

    Returns:
        Dictionary with AI assistance information:
        {
            'has_ai_assistance': bool,
            'ai_tools': List[str],  # Sorted list, e.g., ['Claude', 'Cursor']
            'ai_commits_count': int,  # Number of commits with AI assistance
            'total_commits': int,
            'ai_percentage': float  # Percentage of commits with AI assistance
        }

    Examples:
        >>> commits = [
        ...     {"commit": {"message": "feat: Add feature\\n\\nAssisted-by: Claude"}},
        ...     {"commit": {"message": "fix: Bug fix\\n\\nCode-assisted with Cursor AI"}},
        ... ]
        >>> result = extract_ai_info_from_commits(commits)
        >>> result['has_ai_assistance']
        True
        >>> result['ai_tools']
        ['Claude', 'Cursor']
        >>> result['ai_commits_count']
        2

    Supported patterns (case-insensitive):
        Claude:
            - "assisted-by: claude"
            - "assisted by claude"
            - "co-authored-by: claude"
            - "code-assisted with claude"
            - "code assisted by claude"

        Cursor:
            - "assisted-by: cursor"
            - "assisted by cursor"
            - "co-authored-by: cursor"
            - "code-assisted with cursor" (matches "Code-assisted with Cursor AI")
            - "code assisted by cursor"
    """
    ai_tools = set()
    ai_commits = 0
    total_commits = len(commits)

    # Define detection patterns
    claude_patterns = [
        "assisted-by: claude",
        "assisted by claude",
        "co-authored-by: claude",
        "code-assisted with claude",
        "code assisted by claude",
    ]

    cursor_patterns = [
        "assisted-by: cursor",
        "assisted by cursor",
        "co-authored-by: cursor",
        "code-assisted with cursor",  # Matches "Code-assisted with Cursor AI"
        "code assisted by cursor",
    ]

    for commit in commits:
        message = commit.get("commit", {}).get("message", "")
        message_lower = message.lower()

        # Check for Claude markers
        if any(pattern in message_lower for pattern in claude_patterns):
            ai_tools.add("Claude")
            ai_commits += 1

        # Check for Cursor markers
        if any(pattern in message_lower for pattern in cursor_patterns):
            ai_tools.add("Cursor")
            ai_commits += 1

    return {
        "has_ai_assistance": len(ai_tools) > 0,
        "ai_tools": sorted(list(ai_tools)),
        "ai_commits_count": ai_commits,
        "total_commits": total_commits,
        "ai_percentage": (ai_commits / total_commits * 100) if total_commits > 0 else 0,
    }
