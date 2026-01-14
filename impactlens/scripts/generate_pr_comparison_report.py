#!/usr/bin/env python3
"""
Generate PR AI Impact Comparison Report.

This script reads individual PR phase reports and generates a comparison
report showing metrics across multiple time periods.
"""

import os
import sys
import argparse
import re
from datetime import datetime
from pathlib import Path

from impactlens.core.pr_report_generator import PRReportGenerator
from impactlens.utils.common_args import add_pr_comparison_report_args
from impactlens.utils.report_utils import (
    generate_comparison_report,
    get_identifier_for_file,
    build_pr_project_prefix,
    find_comparison_reports,
    validate_report_files,
    limit_and_display_reports,
    reconcile_phase_names,
)
from impactlens.utils.workflow_utils import (
    load_config_file,
    get_project_root,
    load_members_from_yaml,
)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate PR AI Impact Comparison Report from phase reports"
    )
    add_pr_comparison_report_args(parser)
    args = parser.parse_args()

    # Load phase configuration to get phase names
    project_root = get_project_root()
    default_config_file = project_root / "config" / "pr_report_config.yaml"
    custom_config_file = Path(args.config) if args.config else None

    try:
        phases, _, _, project_settings = load_config_file(default_config_file, custom_config_file)
        phase_names = [phase[0] for phase in phases]  # Extract phase names
    except Exception as e:
        print(f"Warning: Could not load phase names from config: {e}")
        phase_names = []
        project_settings = {}

    # For anonymization consistency: use email if available, otherwise use author
    # This ensures the same person gets the same hash in both Jira and PR reports
    anonymization_identifier = args.author
    if args.author:
        # Try to find email for this author from config
        config_file = custom_config_file if custom_config_file else default_config_file
        if config_file.exists():
            members_detailed = load_members_from_yaml(config_file)
            for member_id, member_info in members_detailed.items():
                if member_info.get("github_username") == args.author:
                    # Found the member, use email for anonymization if available
                    if member_info.get("email"):
                        anonymization_identifier = member_info.get("email")
                    break

    # Find matching reports using shared utility
    report_files = find_comparison_reports(
        report_type="pr",
        identifier=anonymization_identifier,
        reports_dir=args.reports_dir,
        hide_individual_names=args.hide_individual_names,
    )

    # Validate we have enough reports
    if validate_report_files(
        report_files, args.author, args.reports_dir, "pr", args.hide_individual_names
    ):
        return 1

    # Limit to max 4 reports and display
    report_files = limit_and_display_reports(report_files, max_reports=4)

    # Reconcile phase names with report files
    phase_names, report_files = reconcile_phase_names(phase_names, report_files)

    # Generate comparison report using shared utility
    report_gen = PRReportGenerator()

    # Get identifier for filename (normalized and optionally anonymized)
    # Use anonymization_identifier for consistent file naming
    identifier = (
        get_identifier_for_file(anonymization_identifier, args.hide_individual_names)
        if args.author
        else None
    )

    # Build project_prefix from repo owner and name
    project_prefix = build_pr_project_prefix(project_settings)

    generate_comparison_report(
        report_files=report_files,
        report_generator=report_gen,
        phase_names=phase_names,
        identifier=identifier,
        output_dir=args.reports_dir,
        output_file=args.output,
        report_type="pr",
        project_prefix=project_prefix,
        hide_individual_names=args.hide_individual_names,
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
