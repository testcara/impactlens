#!/usr/bin/env python3
"""
Generate Jira AI Impact Analysis Report.

This script orchestrates the complete Jira report generation workflow:
1. Load configuration
2. Generate reports for each configured phase
3. Create comparison report
4. Optionally upload to Google Sheets
"""

import sys
import argparse
import subprocess
import traceback
from pathlib import Path
from typing import List, Optional

from impactlens.utils.workflow_utils import (
    Colors,
    get_project_root,
    cleanup_old_reports,
    upload_to_google_sheets,
    find_latest_comparison_report,
    load_team_members,
    load_and_resolve_config,
    load_team_members_from_yaml,
)
from impactlens.utils.report_utils import (
    normalize_username,
    combine_comparison_reports,
    get_identifier_for_display,
)


def print_header(title: str, subtitle: Optional[str] = None) -> None:
    """Print formatted header."""
    print(f"{Colors.BLUE}{'=' * 40}{Colors.NC}")
    print(f"{Colors.BLUE}{title}{Colors.NC}")
    if subtitle:
        print(f"{Colors.BLUE}{subtitle}{Colors.NC}")
    print(f"{Colors.BLUE}{'=' * 40}{Colors.NC}")
    print()


def generate_phase_report(
    phase_name: str,
    start_date: str,
    end_date: str,
    assignee: Optional[str] = None,
    config_file: Optional[Path] = None,
    leave_days: int = 0,
    capacity: float = 1.0,
    output_dir: Optional[str] = None,
    hide_individual_names: bool = False,
) -> bool:
    """Generate report for a single phase."""
    args = [
        sys.executable,
        "-m",
        "impactlens.scripts.get_jira_metrics",
        "--start",
        start_date,
        "--end",
        end_date,
    ]

    if assignee:
        args.extend(["--assignee", assignee])
    elif config_file and config_file.exists():
        args.extend(["--config", str(config_file)])

    if leave_days > 0:
        args.extend(["--leave-days", str(leave_days)])

    if capacity != 1.0:
        args.extend(["--capacity", str(capacity)])

    if output_dir:
        args.extend(["--output-dir", str(output_dir)])

    if hide_individual_names:
        args.append("--hide-individual-names")

    try:
        subprocess.run(args, check=True)
        return True
    except subprocess.CalledProcessError:
        return False


def generate_comparison_report(
    assignee: Optional[str] = None,
    output_dir: Optional[str] = None,
    config_file: Optional[Path] = None,
    hide_individual_names: bool = False,
) -> bool:
    """Generate comparison report from phase reports."""
    args = [
        sys.executable,
        "-m",
        "impactlens.scripts.generate_jira_comparison_report",
    ]

    if assignee:
        args.extend(["--assignee", assignee])

    if output_dir:
        args.extend(["--reports-dir", str(output_dir)])

    if config_file:
        args.extend(["--config", str(config_file)])

    if hide_individual_names:
        args.append("--hide-individual-names")

    try:
        subprocess.run(args, check=True)
        return True
    except subprocess.CalledProcessError:
        return False


def generate_all_members_reports(
    team_members_file: Path,
    script_name: str,
    no_upload: bool = False,
    upload_members: bool = False,
    config_file: Optional[Path] = None,
    hide_individual_names: bool = False,
) -> int:
    """
    Generate reports for all team members.

    Args:
        team_members_file: Path to config file with team members
        script_name: Script module name to invoke
        no_upload: If True, skip all uploads
        upload_members: If True, upload member reports (default: False, only team report is uploaded)
        config_file: Optional custom config file to pass to subcommands
        hide_individual_names: If True, anonymize individual names in reports
    """
    print_header("Generating reports for all team members")

    members = load_team_members(team_members_file)
    if not members:
        print(f"{Colors.RED}Error: No team members found in {team_members_file}{Colors.NC}")
        return 1

    # Generate team overall report first (always upload unless --no-upload)
    print(f"{Colors.BLUE}>>> Generating Team Overall Report{Colors.NC}")
    print()
    cmd = [sys.executable, "-m", script_name]
    if config_file:
        cmd.extend(["--config", str(config_file)])
    if no_upload:
        cmd.append("--no-upload")
    if hide_individual_names:
        cmd.append("--hide-individual-names")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f"{Colors.RED}  ✗ Failed to generate team report{Colors.NC}")
        return 1
    print()
    print()

    # Generate individual reports for each member
    # Only upload if --upload-members is specified (and --no-upload is not set)
    failed_members = []
    for member in members:
        # Get display identifier for member
        display_member = get_identifier_for_display(member, hide_individual_names)
        print(f"{Colors.BLUE}>>> Generating Report for: {display_member}{Colors.NC}")
        print()
        cmd = [sys.executable, "-m", script_name, member]
        if config_file:
            cmd.extend(["--config", str(config_file)])
        # Skip upload for member reports unless --upload-members is specified
        if no_upload or not upload_members:
            cmd.append("--no-upload")
        if hide_individual_names:
            cmd.append("--hide-individual-names")
        result = subprocess.run(cmd)
        if result.returncode != 0:
            failed_members.append(member)
        print()
        print()

    # Summary
    print(f"{Colors.GREEN}{'=' * 40}{Colors.NC}")
    if failed_members:
        print(
            f"{Colors.YELLOW}⚠ All team member reports completed with {len(failed_members)} failures{Colors.NC}"
        )
        print(f"{Colors.YELLOW}Failed: {', '.join(failed_members)}{Colors.NC}")
    else:
        print(f"{Colors.GREEN}✓ All team member reports completed successfully!{Colors.NC}")
    print(f"{Colors.GREEN}{'=' * 40}{Colors.NC}")
    print()

    print(f"{Colors.BLUE}To combine all reports into a single TSV, run:{Colors.NC}")
    print(f"{Colors.BLUE}  python3 -m {script_name} --combine-only{Colors.NC}")
    print()

    return 0


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate Jira AI Impact Analysis Report",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 -m impactlens.script.generate_jira_report                      # Team overall
  python3 -m impactlens.script.generate_jira_report wlin@redhat.com     # Individual
  python3 -m impactlens.script.generate_jira_report --all-members        # All members
  python3 -m impactlens.script.generate_jira_report --combine-only       # Combine only
        """,
    )

    parser.add_argument(
        "assignee",
        nargs="?",
        help="Assignee email to filter issues (optional)",
    )
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
    parser.add_argument(
        "--hide-individual-names",
        action="store_true",
        help="Anonymize individual names in combined reports (Developer-A3F2, etc.) and hide sensitive fields (leave_days, capacity)",
    )
    parser.add_argument(
        "--config",
        type=str,
        help="Path to custom config YAML file. Settings override defaults from config/jira_report_config.yaml",
        default=None,
    )

    args = parser.parse_args()

    project_root = get_project_root()
    default_config_file = project_root / "config" / "jira_report_config.yaml"
    custom_config_file = Path(args.config) if args.config else None
    default_reports_dir = project_root / "reports" / "jira"

    # Validate, load config, and resolve output directory
    result = load_and_resolve_config(
        custom_config_file, default_config_file, default_reports_dir, "Jira config"
    )
    if result is None:
        return 1

    phases, default_assignee, reports_dir, project_settings = result
    config_file = custom_config_file if custom_config_file else default_config_file

    # Handle --combine-only flag
    if args.combine_only:
        print_header("Combining Existing Jira Reports")

        # Clean up old combined reports before generating new one
        # Note: Only clean combined reports, not comparison reports (which are needed as input)
        print(f"{Colors.YELLOW}Cleaning up old combined reports...{Colors.NC}")
        for old_combined in Path(reports_dir).glob("combined_jira_report_*.tsv"):
            old_combined.unlink()
            print(f"{Colors.GREEN}  ✓ Removed {old_combined.name}{Colors.NC}")
        print()

        # Get project prefix from config
        project_prefix = project_settings.get("jira_project_key")

        try:
            output_file = combine_comparison_reports(
                reports_dir=str(reports_dir),
                report_type="jira",
                title="Jira AI Impact Analysis - Combined Report (Grouped by Metric)",
                project_prefix=project_prefix,
                hide_individual_names=args.hide_individual_names,
            )
            print(f"{Colors.GREEN}✓ Combined report generated: {output_file.name}{Colors.NC}")
            print()
            upload_to_google_sheets(output_file, skip_upload=args.no_upload)
        except Exception as e:
            print(f"{Colors.RED}Error combining reports: {e}{Colors.NC}")
            traceback.logger.debug_exc()
            return 1

        return 0

    # Handle --all-members flag
    if args.all_members:
        return generate_all_members_reports(
            config_file,  # Use same config file for team members
            "impactlens.scripts.generate_jira_report",
            no_upload=args.no_upload,
            upload_members=args.upload_members,
            config_file=config_file,
            hide_individual_names=args.hide_individual_names,
        )

    # Determine assignee
    assignee = args.assignee or default_assignee or None

    if assignee:
        # Get display identifier for assignee
        display_assignee = get_identifier_for_display(assignee, args.hide_individual_names)
        print_header("AI Impact Analysis Report Generator", f"Assignee: {display_assignee}")
    else:
        print_header("AI Impact Analysis Report Generator", "Team Overall Report")

    print()

    # Step 1: Cleanup old reports
    print(f"{Colors.YELLOW}Step 1: Cleaning up old files...{Colors.NC}")
    identifier = normalize_username(assignee) if assignee else "general"
    cleanup_old_reports(reports_dir, identifier, "jira")
    print()

    # Step 2-N: Generate reports for each phase
    step_num = 2
    # Use config file for team members filtering (only when not filtering by assignee)
    team_config_file = config_file if not assignee else None

    # Load leave_days and capacity
    leave_days_list = None
    capacity_list = None
    team_members_details = load_team_members_from_yaml(config_file, detailed=True)

    if assignee:
        # Individual report: get specific member's values
        for member_id, details in team_members_details.items():
            if member_id == assignee or details.get("member") == assignee:
                # Process leave_days
                leave_days_config = details.get("leave_days", 0)
                if isinstance(leave_days_config, list):
                    leave_days_list = leave_days_config
                else:
                    # Single value, use for all phases
                    leave_days_list = [leave_days_config] * len(phases)

                # Process capacity
                capacity_config = details.get("capacity", 1.0)
                if isinstance(capacity_config, list):
                    capacity_list = capacity_config
                else:
                    # Single value, use for all phases
                    capacity_list = [capacity_config] * len(phases)
                break
    else:
        # Team report: aggregate all members' values
        # Initialize lists for each phase
        leave_days_list = [0.0] * len(phases)
        capacity_list = [0.0] * len(phases)

        for member_id, details in team_members_details.items():
            # Process leave_days
            leave_days_config = details.get("leave_days", 0)
            if isinstance(leave_days_config, list):
                for i, ld in enumerate(leave_days_config):
                    if i < len(leave_days_list):
                        leave_days_list[i] += ld
            else:
                # Single value, add to all phases
                for i in range(len(phases)):
                    leave_days_list[i] += leave_days_config

            # Process capacity
            capacity_config = details.get("capacity", 1.0)
            if isinstance(capacity_config, list):
                for i, cap in enumerate(capacity_config):
                    if i < len(capacity_list):
                        capacity_list[i] += cap
            else:
                # Single value, add to all phases
                for i in range(len(phases)):
                    capacity_list[i] += capacity_config

    for phase_index, (phase_name, start_date, end_date) in enumerate(phases):
        print(
            f"{Colors.YELLOW}Step {step_num}: Generating report for '{phase_name}' ({start_date} to {end_date})...{Colors.NC}"
        )

        # Get leave_days for this phase
        phase_leave_days = 0
        if leave_days_list and phase_index < len(leave_days_list):
            phase_leave_days = leave_days_list[phase_index]

        # Get capacity for this phase
        phase_capacity = 1.0
        if capacity_list and phase_index < len(capacity_list):
            phase_capacity = capacity_list[phase_index]

        success = generate_phase_report(
            phase_name,
            start_date,
            end_date,
            assignee=assignee,
            config_file=team_config_file,
            leave_days=phase_leave_days,
            capacity=phase_capacity,
            output_dir=str(reports_dir),
            hide_individual_names=args.hide_individual_names,
        )

        if success:
            print(f"{Colors.GREEN}  ✓ '{phase_name}' report generated{Colors.NC}")
        else:
            print(f"{Colors.RED}  ✗ Failed to generate '{phase_name}' report{Colors.NC}")
            return 1

        print()
        step_num += 1

    # Generate comparison report
    print(f"{Colors.YELLOW}Step {step_num}: Generating comparison report...{Colors.NC}")
    if not generate_comparison_report(
        assignee=assignee,
        output_dir=str(reports_dir),
        config_file=config_file,
        hide_individual_names=args.hide_individual_names,
    ):
        print(f"{Colors.RED}  ✗ Failed to generate comparison report{Colors.NC}")
        return 1
    print()

    # Find and upload the latest comparison report
    comparison_file = find_latest_comparison_report(reports_dir, identifier, "jira")
    if comparison_file:
        print(f"{Colors.GREEN}✓ Report generated: {comparison_file.name}{Colors.NC}")
        print()
        upload_to_google_sheets(comparison_file, skip_upload=args.no_upload)
    else:
        print(f"No comparison file found!")

    print(f"{Colors.GREEN}Done!{Colors.NC}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
