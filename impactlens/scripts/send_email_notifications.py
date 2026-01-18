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

from impactlens.utils.email_notifier import notify_members
from impactlens.utils.anonymization import _global_anonymizer


def collect_members_from_config(config_path: Path) -> List[Dict]:
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
        return config.get("members", [])
    except Exception as e:
        print(f"Warning: Failed to load config {config_path}: {e}")
        return []


def _add_members_to_dict(members: List[Dict], all_members_by_email: Dict[str, Dict]) -> None:
    """
    Helper function to deduplicate and add members to the collection dict.

    Args:
        members: List of member dicts from config
        all_members_by_email: Dict to add members to (modified in place)
    """
    for member in members:
        email = member.get("email")

        if email and "@" in email:
            # Deduplicate by email - keep the member dict as-is
            if email not in all_members_by_email:
                all_members_by_email[email] = member


def collect_all_members(config_dir: Path) -> tuple[List[Dict], bool]:
    """
    Collect all unique team members from configs with email_anonymous_id enabled.

    Logic:
    - If Jira config has email_anonymous_id: true, collect Jira members
    - If PR config has email_anonymous_id: true, collect PR members
    - If both are true, collect and merge (deduplicate) all members
    - Returns True if any config has email enabled, False otherwise

    Supports both single-team and aggregation modes:
    - Single team: Loads from jira_report_config.yaml and/or pr_report_config.yaml in config_dir
    - Aggregation: Loads from aggregation_config.yaml and all sub-project configs

    Args:
        config_dir: Path to config directory

    Returns:
        Tuple of (members list, email_enabled boolean)
    """
    all_members_by_email: Dict[str, Dict] = {}  # email -> member info
    any_email_enabled = False  # Track if any config has email enabled

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

                    if not config_path.exists():
                        continue

                    # Check if email_anonymous_id is enabled in this config
                    from impactlens.utils.workflow_utils import get_email_anonymous_id_enabled

                    if get_email_anonymous_id_enabled(config_path):
                        any_email_enabled = True
                        members = collect_members_from_config(config_path)
                        _add_members_to_dict(members, all_members_by_email)
                        print(
                            f"  ✓ {project}/{config_name}: email_anonymous_id enabled, collected {len(members)} members"
                        )
                    else:
                        print(f"  ✗ {project}/{config_name}: email_anonymous_id disabled")

        except Exception as e:
            print(f"Error loading aggregation config: {e}")
            return [], False

    else:
        # Single team mode: load from config_dir directly
        print(f"Single team mode: {config_dir}")

        for config_name in ["jira_report_config.yaml", "pr_report_config.yaml"]:
            config_path = config_dir / config_name

            if not config_path.exists():
                continue

            # Check if email_anonymous_id is enabled in this config
            from impactlens.utils.workflow_utils import get_email_anonymous_id_enabled

            if get_email_anonymous_id_enabled(config_path):
                any_email_enabled = True
                members = collect_members_from_config(config_path)
                _add_members_to_dict(members, all_members_by_email)
                print(
                    f"  ✓ {config_name}: email_anonymous_id enabled, collected {len(members)} members"
                )
            else:
                print(f"  ✗ {config_name}: email_anonymous_id disabled")

    return list(all_members_by_email.values()), any_email_enabled


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
        "--mail-save-file",
        type=str,
        default=None,
        help="Save emails to files instead of sending them (specify directory path)",
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

    # Collect all team members from configs with email_anonymous_id enabled (deduplicated)
    members, email_enabled = collect_all_members(config_dir)

    if not email_enabled:
        print("ℹ️  Email notifications are disabled in all configs (email_anonymous_id: false)")
        print("=" * 60)
        sys.exit(0)

    if not members:
        print("No team members found in configs with email_anonymous_id enabled")
        print("=" * 60)
        sys.exit(0)

    print(f"Found {len(members)} unique team members\n")

    # Mail save file mode
    if args.mail_save_file:
        print(f"📁 SAVE MODE: Emails will be saved to {args.mail_save_file}/\n")

    # Pre-populate the anonymizer with all team member identifiers
    # This ensures everyone gets a consistent anonymous ID
    # Use normalized email prefix as identifier (e.g., wlin@redhat.com -> wlin)
    from impactlens.utils.report_utils import normalize_username

    print("Generating anonymous identifiers...")
    anon_count = 0
    for member in members:
        email = member.get("email")
        if email and "@" in email:
            identifier = normalize_username(email)
            _global_anonymizer.anonymize(identifier)
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

    # Check SMTP configuration (skip if in save-to-file mode)
    if not args.mail_save_file and not is_smtp_configured() and not args.dry_run:
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

    # Build email mapping using normalized email prefix as identifier
    email_mapping = {}
    for m in members:
        email = m.get("email")
        if email and "@" in email:
            identifier = normalize_username(email)
            email_mapping[identifier] = email

    # Send notifications
    results = notifier.send_batch_notifications(
        name_mapping=_global_anonymizer.get_mapping(),
        email_mapping=email_mapping,
        pr_url=pr_url,
        report_context="ImpactLens Reports Generated",
        dry_run=args.dry_run,
        save_to_file=args.mail_save_file,
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
