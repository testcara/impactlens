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

from impactlens.core.jira_report_generator import JiraReportGenerator
from impactlens.utils.common_args import add_jira_comparison_report_args
from impactlens.utils.report_utils import (
    normalize_username,
    generate_comparison_report,
    get_identifier_for_file,
)
from impactlens.utils.workflow_utils import (
    load_config_file,
    get_project_root,
    load_members_emails,
    load_members_from_yaml,
)


def find_reports(assignee=None, reports_dir="reports/jira", hide_individual_names=False):
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
            # Get file identifier (normalized and optionally anonymized)
            identifier = get_identifier_for_file(assignee, hide_individual_names)
            if f"jira_report_{identifier}_" in filename:
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
    parser = argparse.ArgumentParser(...)
    add_jira_comparison_report_args(parser)
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

    # Assignee must be an email address
    if args.assignee:
        # Validate that assignee exists in config
        if args.assignee not in load_members_emails(config_file):
            raise ValueError(f"Email '{args.assignee}' not found in config file {config_file}")

    # Find matching reports using resolved assignee
    report_files = find_reports(
        args.assignee,
        reports_dir=args.reports_dir,
        hide_individual_names=args.hide_individual_names,
    )

    if len(report_files) == 0:
        if args.assignee:
            print(f"Error: No reports found for assignee '{args.assignee}'")
        else:
            print("Error: No general reports found")
        print("\nLooking for files matching pattern:")
        if args.assignee:
            identifier = get_identifier_for_file(args.assignee, args.hide_individual_names)
            print(f"  {args.reports_dir}/jira_report_{identifier}_*.txt")
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

    # Get identifier for filename (normalized and optionally anonymized)
    identifier = (
        get_identifier_for_file(args.assignee, args.hide_individual_names)
        if args.assignee
        else None
    )

    generate_comparison_report(
        report_files=report_files,
        report_generator=report_gen,
        phase_names=phase_names,
        identifier=identifier,
        output_dir=args.reports_dir,
        output_file=args.output,
        report_type="jira",
        phase_configs=phases,
        hide_individual_names=args.hide_individual_names,
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
