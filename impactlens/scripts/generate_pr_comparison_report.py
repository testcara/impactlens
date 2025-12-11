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
from impactlens.utils.report_utils import generate_comparison_report, get_identifier_for_file
from impactlens.utils.workflow_utils import (
    load_config_file,
    get_project_root,
    load_team_members_from_yaml,
)


def parse_phase_config(config_path="config/github_phases.conf"):
    """Parse phase configuration file."""
    phases = []
    if not os.path.exists(config_path):
        return phases

    with open(config_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    in_array = False
    array_lines = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if "GITHUB_PHASES=(" in line and not stripped.startswith("#"):
            in_array = True
            array_start = line.split("GITHUB_PHASES=(", 1)[1]
            array_lines.append(array_start)
            if ")" in array_start:
                break
            continue
        if in_array:
            array_lines.append(line)
            if ")" in line:
                break

    array_content = "".join(array_lines)
    phase_pattern = r'"([^"]+)"'
    phase_entries = re.findall(phase_pattern, array_content)

    for entry in phase_entries:
        parts = entry.split("|")
        if len(parts) == 3:
            phases.append((parts[0].strip(), parts[1].strip(), parts[2].strip()))

    return phases


def find_reports(author=None, reports_dir="reports/github", hide_individual_names=False):
    """Find all matching PR report files."""
    if not os.path.exists(reports_dir):
        return []

    files = []
    for filename in os.listdir(reports_dir):
        if not filename.startswith("pr_metrics_"):
            continue
        if not filename.endswith(".json"):
            continue

        if author:
            # Get file identifier (normalized and optionally anonymized)
            identifier = get_identifier_for_file(author, hide_individual_names)
            if f"pr_metrics_{identifier}_" in filename:
                files.append(os.path.join(reports_dir, filename))
        else:
            if "pr_metrics_general_" in filename:
                files.append(os.path.join(reports_dir, filename))

    return sorted(files)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate PR AI Impact Comparison Report from phase reports"
    )
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
        "--config",
        type=str,
        help="Path to custom config YAML file",
        default=None,
    )
    parser.add_argument(
        "--hide-individual-names",
        action="store_true",
        help="Look for anonymized report files (Developer-XXXX)",
    )

    args = parser.parse_args()

    # Load phase configuration to get phase names
    project_root = get_project_root()
    default_config_file = project_root / "config" / "pr_report_config.yaml"
    custom_config_file = Path(args.config) if args.config else None

    try:
        phases, _, _, _ = load_config_file(default_config_file, custom_config_file)
        phase_names = [phase[0] for phase in phases]  # Extract phase names
    except Exception as e:
        print(f"Warning: Could not load phase names from config: {e}")
        phase_names = []

    # For anonymization consistency: use email if available, otherwise use author
    # This ensures the same person gets the same hash in both Jira and PR reports
    anonymization_identifier = args.author
    if args.author:
        # Try to find email for this author from config
        config_file = custom_config_file if custom_config_file else default_config_file
        if config_file.exists():
            members_detailed = load_team_members_from_yaml(config_file, detailed=True)
            for member_id, member_info in members_detailed.items():
                if member_info.get("name") == args.author:
                    # Found the member, use email for anonymization if available
                    if member_info.get("email"):
                        anonymization_identifier = member_info.get("email")
                    break

    # Find matching reports
    # Use anonymization_identifier for file lookup (must match file naming convention)
    report_files = find_reports(
        anonymization_identifier,
        reports_dir=args.reports_dir,
        hide_individual_names=args.hide_individual_names,
    )

    if len(report_files) == 0:
        if args.author:
            print(f"Error: No reports found for author '{args.author}'")
        else:
            print("Error: No general reports found")
        print("\nLooking for files matching pattern:")
        if args.author:
            identifier = get_identifier_for_file(
                anonymization_identifier, args.hide_individual_names
            )
            print(f"  {args.reports_dir}/pr_metrics_{identifier}_*.json")
        else:
            print(f"  {args.reports_dir}/pr_metrics_general_*.json")
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
    report_gen = PRReportGenerator()

    # Get identifier for filename (normalized and optionally anonymized)
    # Use anonymization_identifier for consistent file naming
    identifier = (
        get_identifier_for_file(anonymization_identifier, args.hide_individual_names)
        if args.author
        else None
    )

    generate_comparison_report(
        report_files=report_files,
        report_generator=report_gen,
        phase_names=phase_names,
        identifier=identifier,
        output_dir=args.reports_dir,
        output_file=args.output,
        report_type="pr",
        hide_individual_names=args.hide_individual_names,
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
