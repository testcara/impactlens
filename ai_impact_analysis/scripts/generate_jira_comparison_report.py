#!/usr/bin/env python3
"""
Generate Jira AI Impact Comparison Report.

This script reads individual Jira phase reports and generates a comparison
report showing metrics across multiple time periods.
"""

import os
import sys
import argparse
from datetime import datetime
from pathlib import Path

from ai_impact_analysis.core.jira_report_generator import JiraReportGenerator
from ai_impact_analysis.utils.report_utils import normalize_username, generate_comparison_report
from ai_impact_analysis.utils.workflow_utils import (
    load_config_file,
    get_project_root,
    load_team_members_from_yaml,
    resolve_member_identifier,
)


def find_reports(assignee=None, reports_dir="reports/jira"):
    """Find all matching Jira report files."""
    if not os.path.exists(reports_dir):
        return []

    files = []
    for filename in os.listdir(reports_dir):
        if not filename.startswith("jira_report_"):
            continue
        if not filename.endswith(".txt"):
            continue

        if assignee:
            username = normalize_username(assignee)
            if f"jira_report_{username}_" in filename:
                files.append(os.path.join(reports_dir, filename))
        else:
            if "jira_report_general_" in filename:
                files.append(os.path.join(reports_dir, filename))

    return sorted(files)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate Jira AI Impact Comparison Report from phase reports"
    )
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
        "--config",
        type=str,
        help="Path to custom config YAML file",
        default=None,
    )
    args = parser.parse_args()

    # Load phase configuration to get phase names
    project_root = get_project_root()
    default_config_file = project_root / "config" / "jira_report_config.yaml"
    custom_config_file = Path(args.config) if args.config else None

    try:
        phases, _, _, _ = load_config_file(default_config_file, custom_config_file)
        phase_names = [phase[0] for phase in phases]  # Extract phase names
    except Exception as e:
        print(f"Warning: Could not load phase names from config: {e}")
        phase_names = []

    # Use custom config if provided, otherwise use default
    config_file = custom_config_file if custom_config_file else default_config_file

    # Resolve member identifier (supports both "wlin" and "wlin@redhat.com")
    resolved_assignee = args.assignee
    if args.assignee:
        email, _ = resolve_member_identifier(args.assignee, config_file)
        if email:
            resolved_assignee = email
            if email != args.assignee:
                print(f"Resolved '{args.assignee}' to '{email}'")

    # Find matching reports using resolved assignee
    report_files = find_reports(resolved_assignee, reports_dir=args.reports_dir)

    if len(report_files) == 0:
        if args.assignee:
            print(f"Error: No reports found for assignee '{args.assignee}'")
        else:
            print("Error: No general reports found")
        print("\nLooking for files matching pattern:")
        if args.assignee:
            username = normalize_username(args.assignee)
            print(f"  {args.reports_dir}/jira_report_{username}_*.txt")
        else:
            print(f"  {args.reports_dir}/jira_report_general_*.txt")
        return 1

    if len(report_files) < 2:
        print(f"Warning: Found only {len(report_files)} report(s), need at least 2 for comparison")
        print(f"Found: {', '.join(report_files)}")
        return 1

    # Use all reports if <= 4, otherwise use the most recent 4
    if len(report_files) > 4:
        print(f"Found {len(report_files)} reports, using the 4 most recent for comparison:")
        report_files = sorted(report_files)[-4:]
    else:
        report_files = sorted(report_files)

    print(f"Analyzing {len(report_files)} reports:")
    for i, f in enumerate(report_files, 1):
        print(f"  Phase {i}: {f}")
    print()

    # Use phase names from config, limit report files to match config phases
    if phase_names and len(report_files) > len(phase_names):
        print(
            f"Warning: Found {len(report_files)} reports but config only has {len(phase_names)} phases"
        )
        print(f"Using only the {len(phase_names)} most recent reports to match config")
        report_files = sorted(report_files)[-len(phase_names) :]
    elif not phase_names:
        # No config available, use generic names for all found reports
        phase_names = [f"Phase {i+1}" for i in range(len(report_files))]

    # Generate comparison report using shared utility
    report_gen = JiraReportGenerator()
    identifier = normalize_username(resolved_assignee) if resolved_assignee else None

    generate_comparison_report(
        report_files=report_files,
        report_generator=report_gen,
        phase_names=phase_names,
        identifier=identifier,
        output_dir=args.reports_dir,
        output_file=args.output,
        report_type="jira",
        phase_configs=phases,
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
