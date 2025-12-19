#!/usr/bin/env python3
"""
Send email notifications to team members about their anonymous identifiers.

This script collects team members from all relevant config files, deduplicates them,
and sends a single email notification to each person with their anonymous identifier.

Usage:
    python -m impactlens.scripts.send_email_notifications --config-dir <config_dir>
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Dict, List
import yaml

from impactlens.utils.email_notifier import notify_team_members
from impactlens.utils.anonymization import _global_anonymizer


def collect_team_members_from_config(config_path: Path) -> List[Dict]:
    """
    Collect team members from a single config file.

    Args:
        config_path: Path to a config file (jira_report_config.yaml or pr_report_config.yaml)

    Returns:
        List of team member dictionaries
    """
    if not config_path.exists():
        return []

    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        return config.get("team_members", [])
    except Exception as e:
        print(f"Warning: Failed to load config {config_path}: {e}")
        return []


def load_email_config(config_path: Path) -> Dict:
    """
    Load email notification configuration from a config file.

    Args:
        config_path: Path to config file

    Returns:
        Dict with email notification settings (enabled flag only)
    """
    if not config_path.exists():
        return None

    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        # Support multiple config names for backward compatibility
        email_config = (
            config.get("email_anonymous_id")
            or config.get("share_anonymous_id")
            or config.get("email_notifications_for_identifier")
            or config.get("email_notifications", {})
        )
        return email_config
    except Exception as e:
        print(f"Warning: Failed to load email config from {config_path}: {e}")
        return {}


def _add_members_to_dict(members: List[Dict], all_members_by_email: Dict[str, Dict]) -> None:
    """
    Helper function to deduplicate and add members to the collection dict.

    Args:
        members: List of member dicts from config
        all_members_by_email: Dict to add members to (modified in place)
    """
    for member in members:
        email = member.get("email")
        name = member.get("member") or member.get("name")

        if email and name and "@" in email:
            # Deduplicate by email
            if email not in all_members_by_email:
                all_members_by_email[email] = {"member": name, "email": email}


def collect_all_team_members(config_dir: Path) -> tuple[List[Dict], Dict]:
    """
    Collect all unique team members and email config from config directory.

    Supports both single-team and aggregation modes:
    - Single team: Loads from jira_report_config.yaml and/or pr_report_config.yaml in config_dir
    - Aggregation: Loads from aggregation_config.yaml and all sub-project configs

    Args:
        config_dir: Path to config directory

    Returns:
        Tuple of (team_members list, email_config dict)
    """
    all_members_by_email: Dict[str, Dict] = {}  # email -> member info
    email_config = {}  # Will use first valid email config found

    # Check if this is aggregation mode
    aggregation_config = config_dir / "aggregation_config.yaml"

    if aggregation_config.exists():
        # Aggregation mode: collect from all sub-projects
        print(f"Aggregation mode detected: {aggregation_config}")

        try:
            with open(aggregation_config, "r") as f:
                agg_config = yaml.safe_load(f)

            projects = agg_config.get("aggregation", {}).get("projects", [])
            print(f"Found {len(projects)} projects: {', '.join(projects)}")

            for project in projects:
                project_dir = config_dir / project

                # Try both jira and pr config files
                for config_name in ["jira_report_config.yaml", "pr_report_config.yaml"]:
                    config_path = project_dir / config_name
                    members = collect_team_members_from_config(config_path)

                    # Load email config from first available config
                    if not email_config:
                        email_config = load_email_config(config_path) or {}

                    _add_members_to_dict(members, all_members_by_email)

        except Exception as e:
            print(f"Error loading aggregation config: {e}")
            return []

    else:
        # Single team mode: load from config_dir directly
        print(f"Single team mode: {config_dir}")

        for config_name in ["jira_report_config.yaml", "pr_report_config.yaml"]:
            config_path = config_dir / config_name
            members = collect_team_members_from_config(config_path)

            # Load email config from first available config
            if not email_config:
                email_config = load_email_config(config_path) or {}

            _add_members_to_dict(members, all_members_by_email)

    return list(all_members_by_email.values()), email_config


def main():
    """Main function to send email notifications."""
    parser = argparse.ArgumentParser(
        description="Send email notifications to team members about their anonymous identifiers"
    )
    parser.add_argument(
        "--config-dir",
        required=True,
        help="Config directory (e.g., config/team-a or config/aggregation)",
    )
    parser.add_argument(
        "--test-mode",
        action="store_true",
        help="Test mode: only send emails to wlin@redhat.com (for testing without spamming team)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="[Development only] Print emails without sending them",
    )

    args = parser.parse_args()

    config_dir = Path(args.config_dir)

    if not config_dir.exists():
        print(f"Error: Config directory not found: {config_dir}")
        sys.exit(1)

    print("=" * 60)
    print("Sending Email Notifications for Anonymous Identifiers")
    print("=" * 60)
    print(f"Config directory: {config_dir}\n")

    # Collect all team members and email config (deduplicated)
    team_members, email_config = collect_all_team_members(config_dir)

    if not team_members:
        print("No team members found in config files")
        print("=" * 60)
        sys.exit(0)

    print(f"Found {len(team_members)} unique team members\n")

    # Check if email notifications are enabled
    if not email_config.get("enabled", True):
        print("ℹ️  Email notifications are disabled in config (email_notifications.enabled = false)")
        print("=" * 60)
        sys.exit(0)

    # Test mode: filter to only wlin@redhat.com
    if args.test_mode:
        original_count = len(team_members)
        team_members = [m for m in team_members if m.get("email") == "wlin@redhat.com"]
        print(
            f"🧪 TEST MODE: Filtered {original_count} members to {len(team_members)} (only wlin@redhat.com)"
        )
        print("   This prevents spamming the team during testing\n")

        if not team_members:
            print("⚠️  No test email (wlin@redhat.com) found in team members")
            print("   Add wlin@redhat.com to your config for testing")
            print("=" * 60)
            sys.exit(0)

    # Pre-populate the anonymizer with all team member names
    # This ensures everyone gets a consistent anonymous ID
    print("Generating anonymous identifiers...")
    anon_count = 0
    for member in team_members:
        name = member.get("member") or member.get("name")
        if name:
            _global_anonymizer.anonymize(name)
            anon_count += 1
    print(f"  Generated {anon_count} anonymous identifiers\n")

    # Get PR URL from environment (if in CI)
    pr_url = os.getenv("GITHUB_PR_URL")

    # Get SMTP configuration using centralized utility
    from impactlens.utils.smtp_config import (
        get_smtp_config,
        create_email_notifier,
        is_smtp_configured,
        print_smtp_config_summary,
    )

    smtp_config = get_smtp_config()
    print_smtp_config_summary(smtp_config)

    # Check SMTP configuration
    if not is_smtp_configured() and not args.dry_run:
        print("\n" + "=" * 60)
        print("⚠️  SMTP Configuration Required")
        print("=" * 60)
        print("\nTo send email notifications, you need to configure SMTP settings.")
        print("\nAdd the following environment variables:")
        print("  - SMTP_HOST (e.g., smtp.gmail.com)")
        print("  - SMTP_PORT (e.g., 587)")
        print("  - SMTP_USER")
        print("  - SMTP_PASSWORD")
        print("  - FROM_EMAIL")
        print("\nFor GitHub Actions, add these as repository secrets.")
        print("For local use, add them to your .env file.")
        print("\nSee .env.example for details.")
        print("\nFor development/testing, use --dry-run flag.")
        print("=" * 60)
        sys.exit(1)

    # Dry-run mode (development only)
    if args.dry_run:
        print("ℹ️  Dry-run mode enabled - emails will be printed but not sent\n")

    # Create EmailNotifier with SMTP configuration
    notifier = create_email_notifier(smtp_config)

    # Send notifications
    results = notifier.send_batch_notifications(
        name_mapping=_global_anonymizer.get_mapping(),
        email_mapping={m.get("member") or m.get("name"): m.get("email") for m in team_members},
        pr_url=pr_url,
        report_context="ImpactLens Reports Generated",
        dry_run=args.dry_run,
    )

    # Summary
    if results:
        success_count = sum(1 for v in results.values() if v)
        print(f"\n✓ Email notifications completed: {success_count}/{len(results)} sent")
    else:
        print("\n⚠️  No emails were sent")

    print("=" * 60)


if __name__ == "__main__":
    main()
