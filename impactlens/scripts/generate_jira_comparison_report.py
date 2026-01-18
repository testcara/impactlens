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
    generate_comparison_report,
    get_identifier_for_file,
    find_comparison_reports,
    validate_report_files,
    limit_and_display_reports,
    reconcile_phase_names,
)
from impactlens.utils.workflow_utils import (
    load_config_file,
    get_project_root,
    load_members_emails,
    load_members_from_yaml,
)


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
        _, root_configs = load_config_file(default_config_file, custom_config_file)
        phases = root_configs["phases"]
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

    # Find matching reports using shared utility
    report_files = find_comparison_reports(
        report_type="jira",
        identifier=args.assignee,
        reports_dir=args.reports_dir,
        hide_individual_names=args.hide_individual_names,
    )

    # Validate we have enough reports
    if validate_report_files(
        report_files, args.assignee, args.reports_dir, "jira", args.hide_individual_names
    ):
        return 1

    # Limit to max 4 reports and display
    report_files = limit_and_display_reports(report_files, max_reports=4)

    # Reconcile phase names with report files
    phase_names, report_files = reconcile_phase_names(phase_names, report_files)

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
