"""
Common argument definitions for ImpactLens scripts.

This module provides reusable argument groups to ensure consistency across all scripts.
Arguments are organized into logical groups based on functionality.
"""

import argparse


# ============================================================================
# Core Arguments - Used by most scripts
# ============================================================================


def add_config_arg(parser: argparse.ArgumentParser) -> None:
    """Add config file path argument."""
    parser.add_argument(
        "--config",
        type=str,
        help="Path to custom config YAML file",
        default=None,
    )


def add_date_range_args(parser: argparse.ArgumentParser, required: bool = True) -> None:
    """Add start and end date arguments for time-based queries."""
    parser.add_argument(
        "--start",
        type=str,
        help="Start date (format: YYYY-MM-DD)",
        required=required,
        default=None,
    )
    parser.add_argument(
        "--end",
        type=str,
        help="End date (format: YYYY-MM-DD)",
        required=required,
        default=None,
    )


def add_output_dir_arg(parser: argparse.ArgumentParser, default: str = "reports") -> None:
    """Add output directory argument."""
    parser.add_argument(
        "--output-dir",
        type=str,
        help=f"Output directory for reports (default: {default})",
        default=default,
    )


# ============================================================================
# Report Generation Arguments
# ============================================================================


def add_report_generation_args(parser: argparse.ArgumentParser) -> None:
    """Add common arguments for report generation scripts."""
    parser.add_argument(
        "--all-members",
        action="store_true",
        help="Generate reports for all team members from config",
    )
    parser.add_argument(
        "--combine-only",
        action="store_true",
        help="Combine existing TSV reports without regenerating",
    )


# ============================================================================
# Upload & Privacy Arguments
# ============================================================================


def add_upload_args(parser: argparse.ArgumentParser) -> None:
    """Add Google Sheets upload arguments."""
    parser.add_argument(
        "--no-upload",
        action="store_true",
        help="Skip uploading report to Google Sheets",
    )
    parser.add_argument(
        "--upload-members",
        action="store_true",
        help="Upload individual member reports to Google Sheets (default: only team and combined reports)",
    )


def add_anonymization_arg(parser: argparse.ArgumentParser) -> None:
    """Add anonymization argument for privacy protection."""
    parser.add_argument(
        "--hide-individual-names",
        action="store_true",
        help="Anonymize individual names in reports (Developer-XXXX)",
    )


# ============================================================================
# Jira-Specific Arguments
# ============================================================================


def add_jira_assignee_arg(parser: argparse.ArgumentParser, required: bool = False) -> None:
    """Add Jira assignee argument (positional or optional)."""
    if required:
        parser.add_argument(
            "assignee",
            help="Assignee email to filter issues",
        )
    else:
        parser.add_argument(
            "assignee",
            nargs="?",
            help="Assignee email to filter issues (optional)",
        )


def add_jira_filter_args(parser: argparse.ArgumentParser) -> None:
    """Add Jira filtering arguments (status, project, assignee)."""
    parser.add_argument(
        "--status",
        type=str,
        help="Issue status (default: Done)",
        default="Done",
    )
    parser.add_argument(
        "--project",
        type=str,
        help="Project key (overrides PROJECT_KEY in config)",
        default=None,
    )
    parser.add_argument(
        "--assignee",
        type=str,
        help="Specify assignee (username or email)",
        default=None,
    )


def add_jira_comparison_args(parser: argparse.ArgumentParser) -> None:
    """Add arguments for Jira comparison reports."""
    parser.add_argument(
        "--assignee",
        type=str,
        help="Filter by assignee (e.g., sbudhwar or sbudhwar@redhat.com)",
        default=None,
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output filename (default: auto-generated)",
        default=None,
    )
    parser.add_argument(
        "--reports-dir",
        type=str,
        help="Reports directory (default: reports/jira)",
        default="reports/jira",
    )
    parser.add_argument(
        "--hide-individual-names",
        action="store_true",
        help="Anonymize individual names in reports",
    )


# ============================================================================
# GitHub PR-Specific Arguments
# ============================================================================


def add_pr_author_arg(parser: argparse.ArgumentParser, required: bool = False) -> None:
    """Add GitHub author argument (positional or optional)."""
    if required:
        parser.add_argument(
            "author",
            help="GitHub author username to filter PRs",
        )
    else:
        parser.add_argument(
            "author",
            nargs="?",
            help="GitHub author username to filter PRs (optional)",
        )


def add_pr_filter_args(parser: argparse.ArgumentParser) -> None:
    """Add PR filtering arguments."""
    parser.add_argument(
        "--author",
        type=str,
        help="Filter by author (GitHub username)",
        default=None,
    )
    parser.add_argument(
        "--incremental",
        action="store_true",
        help="Only fetch new/updated PRs (faster for repeated runs)",
    )


def add_pr_api_args(parser: argparse.ArgumentParser) -> None:
    """Add GitHub API selection and caching arguments."""
    parser.add_argument(
        "--use-graphql",
        action="store_true",
        default=True,
        help="Use GraphQL API (faster, default: True)",
    )
    parser.add_argument(
        "--use-rest",
        action="store_true",
        help="Use REST API (legacy mode, slower)",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable caching (GraphQL only)",
    )
    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="Clear cache before fetching (GraphQL only)",
    )


def add_pr_comparison_args(parser: argparse.ArgumentParser) -> None:
    """Add arguments for PR comparison reports."""
    parser.add_argument(
        "--author",
        type=str,
        help="Filter by author (GitHub username)",
        default=None,
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output filename (default: auto-generated)",
        default=None,
    )
    parser.add_argument(
        "--reports-dir",
        type=str,
        help="Reports directory (default: reports/github)",
        default="reports/github",
    )
    parser.add_argument(
        "--hide-individual-names",
        action="store_true",
        help="Anonymize individual names in reports",
    )


# ============================================================================
# Capacity & Workload Arguments
# ============================================================================


def add_capacity_args(parser: argparse.ArgumentParser) -> None:
    """Add leave days and work capacity arguments for accurate throughput calculation."""
    parser.add_argument(
        "--leave-days",
        type=str,
        help="Number of leave days for this phase (e.g., '26' or '11.5')",
        default=None,
    )
    parser.add_argument(
        "--capacity",
        type=str,
        help="Work capacity for this member (0.0 to 1.0, e.g., '0.8' for 80%% time)",
        default=None,
    )


# ============================================================================
# Analysis & Insights Arguments
# ============================================================================


def add_claude_analysis_args(parser: argparse.ArgumentParser) -> None:
    """Add arguments for Claude-based analysis (analyze_with_claude_code.py)."""
    parser.add_argument(
        "--reports-dir",
        type=str,
        required=True,
        help="Path to TSV report (supports wildcards for latest)",
    )
    parser.add_argument(
        "--prompt-template",
        type=str,
        default="config/analysis_prompt_template.yaml",
        help="Path to prompt template YAML file",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="reports",
        help="Output directory for analysis",
    )
    parser.add_argument(
        "--save-analysis",
        type=str,
        help="Analysis text to save directly (optional, skips Claude Code call)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Timeout for Claude Code analysis in seconds (default: 300)",
    )
    parser.add_argument(
        "--prompt-only",
        action="store_true",
        help="Prompt preview mode: only generate and display prompt without calling Claude",
    )
    parser.add_argument(
        "--no-upload",
        action="store_true",
        help="Skip uploading analysis to Google Sheets (default: auto-upload)",
    )
    parser.add_argument(
        "--claude-api-mode",
        action="store_true",
        help="Use Anthropic API instead of Claude Code CLI (requires ANTHROPIC_API_KEY)",
    )
    parser.add_argument(
        "--anthropic-api-key",
        type=str,
        help="Anthropic API key (if not provided, reads from ANTHROPIC_API_KEY env var)",
    )


def add_aggregation_args(parser: argparse.ArgumentParser) -> None:
    """Add arguments for report aggregation."""
    parser.add_argument(
        "--jira-only",
        action="store_true",
        help="Aggregate only Jira reports",
    )
    parser.add_argument(
        "--pr-only",
        action="store_true",
        help="Aggregate only PR reports",
    )


# ============================================================================
# Email Notification Arguments
# ============================================================================


def add_email_notification_args(parser: argparse.ArgumentParser) -> None:
    """Add arguments for email notifications."""
    parser.add_argument(
        "--mail-save-file",
        type=str,
        default=None,
        help="Save emails to files instead of sending them (specify directory path)",
    )


# ============================================================================
# Composite Argument Groups - Common Combinations
# ============================================================================


def add_jira_metrics_args(parser: argparse.ArgumentParser) -> None:
    """Add all arguments for Jira metrics scripts (get_jira_metrics.py)."""
    add_date_range_args(parser, required=True)
    add_jira_filter_args(parser)
    add_capacity_args(parser)
    add_output_dir_arg(parser, default="reports/jira")
    add_anonymization_arg(parser)
    add_config_arg(parser)


def add_pr_metrics_args(parser: argparse.ArgumentParser) -> None:
    """Add all arguments for PR metrics scripts (get_pr_metrics.py)."""
    add_date_range_args(parser, required=True)
    add_pr_filter_args(parser)
    add_pr_api_args(parser)
    add_capacity_args(parser)
    add_output_dir_arg(parser, default="reports/github")
    add_anonymization_arg(parser)
    add_config_arg(parser)


def add_jira_report_args(parser: argparse.ArgumentParser) -> None:
    """Add all arguments for Jira report generation scripts."""
    add_jira_assignee_arg(parser, required=False)
    add_config_arg(parser)
    add_report_generation_args(parser)
    add_upload_args(parser)
    add_anonymization_arg(parser)


def add_pr_report_args(parser: argparse.ArgumentParser) -> None:
    """Add all arguments for PR report generation scripts."""
    add_pr_author_arg(parser, required=False)
    add_pr_filter_args(parser)
    add_config_arg(parser)
    add_report_generation_args(parser)
    add_upload_args(parser)
    add_anonymization_arg(parser)


def add_jira_comparison_report_args(parser: argparse.ArgumentParser) -> None:
    """Add all arguments for Jira comparison report scripts."""
    add_jira_comparison_args(parser)
    add_config_arg(parser)


def add_pr_comparison_report_args(parser: argparse.ArgumentParser) -> None:
    """Add all arguments for PR comparison report scripts."""
    add_pr_comparison_args(parser)
    add_config_arg(parser)


def add_aggregate_reports_args(parser: argparse.ArgumentParser) -> None:
    """Add all arguments for report aggregation scripts."""
    parser.add_argument(
        "--config",
        type=str,
        required=True,
        help="Path to aggregation config file (YAML)",
    )
    add_aggregation_args(parser)
    add_upload_args(parser)


def add_upload_to_sheets_args(parser: argparse.ArgumentParser) -> None:
    """Add all arguments for upload_to_sheets script."""
    parser.add_argument(
        "--report",
        type=str,
        required=True,
        help="Path to TSV/CSV report file to upload",
    )
    parser.add_argument(
        "--credentials",
        type=str,
        help="Path to Google credentials JSON file (or set GOOGLE_CREDENTIALS_FILE env var)",
        default=None,
    )
    parser.add_argument(
        "--spreadsheet-id",
        type=str,
        help="Existing spreadsheet ID to update (or set GOOGLE_SPREADSHEET_ID env var)",
        default=None,
    )
    parser.add_argument(
        "--sheet-name",
        type=str,
        help="Name for the sheet tab (default: derived from filename)",
        default=None,
    )
    parser.add_argument(
        "--no-format",
        action="store_true",
        help="Skip formatting (frozen header, bold, etc)",
    )
    add_config_arg(parser)  # For extracting sheet prefix
