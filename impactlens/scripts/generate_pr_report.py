#!/usr/bin/env python3
"""
Generate GitHub PR AI Impact Analysis Report.

This script orchestrates the complete GitHub PR report generation workflow:
1. Load configuration
2. Generate PR metrics for each configured phase
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
    load_team_members_from_yaml,
    load_and_resolve_config,
)
from impactlens.utils.report_utils import (
    normalize_username,
    combine_comparison_reports,
    get_identifier_for_display,
    build_pr_project_prefix,
)
from impactlens.core.report_aggregator import ReportAggregator


def print_header(title: str, subtitle: Optional[str] = None) -> None:
    """Print formatted header."""
    print(f"{Colors.BLUE}{'=' * 40}{Colors.NC}")
    print(f"{Colors.BLUE}{title}{Colors.NC}")
    if subtitle:
        print(f"{Colors.BLUE}{subtitle}{Colors.NC}")
    print(f"{Colors.BLUE}{'=' * 40}{Colors.NC}")
    print()


def generate_phase_metrics(
    phase_name: str,
    start_date: str,
    end_date: str,
    author: Optional[str] = None,
    incremental: bool = False,
    output_dir: Optional[str] = None,
    hide_individual_names: bool = False,
    config_file: Optional[Path] = None,
) -> bool:
    """Generate PR metrics for a single phase."""
    args = [
        sys.executable,
        "-m",
        "impactlens.scripts.get_pr_metrics",
        "--start",
        start_date,
        "--end",
        end_date,
    ]

    if author:
        args.extend(["--author", author])

    if incremental:
        args.append("--incremental")

    if output_dir:
        args.extend(["--output-dir", str(output_dir)])

    if hide_individual_names:
        args.append("--hide-individual-names")

    if config_file:
        args.extend(["--config", str(config_file)])

    try:
        subprocess.run(args, check=True)
        return True
    except subprocess.CalledProcessError:
        return False


def generate_comparison_report(
    author: Optional[str] = None,
    output_dir: Optional[str] = None,
    config_file: Optional[Path] = None,
    hide_individual_names: bool = False,
) -> bool:
    """Generate comparison report from phase metrics."""
    args = [
        sys.executable,
        "-m",
        "impactlens.scripts.generate_pr_comparison_report",
    ]

    if author:
        args.extend(["--author", author])

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
        config_file: Optional custom config file path
        hide_individual_names: If True, anonymize individual names in reports
    """
    print_header("Generating reports for all team members")

    # Load detailed member information (includes both name and email)
    members_detailed = load_team_members_from_yaml(team_members_file, detailed=True)
    if not members_detailed:
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
    for member_id, member_info in members_detailed.items():
        # Use 'name' (GitHub username) for API query
        # The script will automatically look up email from config for anonymization
        github_username = member_info.get("name") or member_id
        member_email = member_info.get("email")

        # Get display identifier for member (use email for anonymization if available)
        display_identifier = member_email if member_email else github_username
        display_member = get_identifier_for_display(display_identifier, hide_individual_names)
        print(f"{Colors.BLUE}>>> Generating Report for: {display_member}{Colors.NC}")
        print()

        # Pass GitHub username for API query
        # The script will find the corresponding email from config automatically
        cmd = [sys.executable, "-m", script_name, github_username]
        if config_file:
            cmd.extend(["--config", str(config_file)])
        # Skip upload for member reports unless --upload-members is specified
        if no_upload or not upload_members:
            cmd.append("--no-upload")
        if hide_individual_names:
            cmd.append("--hide-individual-names")
        result = subprocess.run(cmd)
        if result.returncode != 0:
            failed_members.append(github_username)
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
        description="Generate GitHub PR AI Impact Analysis Report",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 -m impactlens.script.generate_pr_report                    # Team overall
  python3 -m impactlens.script.generate_pr_report wlin              # Individual
  python3 -m impactlens.script.generate_pr_report --all-members      # All members
  python3 -m impactlens.script.generate_pr_report --combine-only     # Combine only
  python3 -m impactlens.script.generate_pr_report --incremental      # Incremental mode
        """,
    )

    parser.add_argument(
        "author",
        nargs="?",
        help="GitHub author username to filter PRs (optional)",
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
        "--incremental",
        action="store_true",
        help="Only fetch new/updated PRs (faster for repeated runs)",
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
        help="Anonymize individual names in combined reports (Developer-A3F2, etc.)",
    )
    parser.add_argument(
        "--config",
        type=str,
        help="Path to custom config file (default: config/pr_report_config.yaml)",
    )

    args = parser.parse_args()

    project_root = get_project_root()
    default_config_file = project_root / "config" / "pr_report_config.yaml"
    custom_config_file = Path(args.config) if args.config else None
    default_reports_dir = project_root / "reports" / "github"

    # Validate, load config, and resolve output directory
    result = load_and_resolve_config(
        custom_config_file, default_config_file, default_reports_dir, "PR config"
    )
    if result is None:
        return 1

    phases, default_author, reports_dir, project_settings = result
    config_file = custom_config_file if custom_config_file else default_config_file

    # Handle --combine-only flag
    if args.combine_only:
        print_header("Combining Existing GitHub PR Reports")

        # Clean up old combined reports before generating new one
        # Note: Only clean combined reports, not comparison reports (which are needed as input)
        print(f"{Colors.YELLOW}Cleaning up old combined reports...{Colors.NC}")
        for old_combined in Path(reports_dir).glob("combined_pr_report_*.tsv"):
            old_combined.unlink()
            print(f"{Colors.GREEN}  ✓ Removed {old_combined.name}{Colors.NC}")
        print()

        try:
            # Build project_prefix from repo owner and name
            project_prefix = build_pr_project_prefix(project_settings)

            output_file = combine_comparison_reports(
                reports_dir=str(reports_dir),
                report_type="pr",
                title="GitHub PR AI Impact Analysis - Combined Report (Grouped by Metric)",
                project_prefix=project_prefix,
                hide_individual_names=args.hide_individual_names,
            )
            print(f"{Colors.GREEN}✓ Combined report generated: {output_file.name}{Colors.NC}")
            print()

            # Upload to Google Sheets if not disabled
            upload_to_google_sheets(output_file, skip_upload=args.no_upload)

            print()
            print(f"{Colors.GREEN}{'=' * 40}{Colors.NC}")
            print(f"{Colors.GREEN}✓ Combined report completed successfully!{Colors.NC}")
            print(f"{Colors.GREEN}{'=' * 40}{Colors.NC}")

        except Exception as e:
            print(f"{Colors.RED}Error combining reports: {e}{Colors.NC}")
            return 1

        # Check if aggregation config exists and run aggregation
        # Look for aggregation_config.yaml in two places:
        # 1. Same directory as the config file (for single team)
        # 2. Parent directory (for multi-team with aggregation at parent level)
        config_dir = config_file.parent
        aggregation_config = config_dir / "aggregation_config.yaml"
        if not aggregation_config.exists():
            aggregation_config = config_dir.parent / "aggregation_config.yaml"

        if aggregation_config.exists():
            print()
            print(f"{Colors.BLUE}{'=' * 40}{Colors.NC}")
            print(f"{Colors.BLUE}Found aggregation config, running aggregation...{Colors.NC}")
            print(f"{Colors.BLUE}{'=' * 40}{Colors.NC}")
            print()
            try:
                aggregator = ReportAggregator(str(aggregation_config))
                pr_output = aggregator.aggregate_pr_reports()
                if pr_output:
                    print(f"{Colors.GREEN}✓ PR aggregation completed: {pr_output.name}{Colors.NC}")
                else:
                    print(f"{Colors.YELLOW}⚠ No PR reports found for aggregation{Colors.NC}")
            except Exception as e:
                print(f"{Colors.RED}Error during aggregation: {e}{Colors.NC}")
                # Don't fail the whole script if aggregation fails
                traceback.print_exc()

        return 0

    # Handle --all-members flag
    if args.all_members:
        return generate_all_members_reports(
            config_file,  # Use same config file for team members
            "impactlens.scripts.generate_pr_report",
            no_upload=args.no_upload,
            upload_members=args.upload_members,
            config_file=config_file,
            hide_individual_names=args.hide_individual_names,
        )

    # Determine author
    author = args.author or default_author or None

    # For anonymization consistency: use email if available, otherwise use author
    # This ensures the same person gets the same hash in both Jira and PR reports
    anonymization_identifier = author
    if author:
        # Try to find email for this author from config
        members_detailed = load_team_members_from_yaml(config_file, detailed=True)
        for member_id, member_info in members_detailed.items():
            if member_info.get("name") == author:
                # Found the member, use email for anonymization if available
                if member_info.get("email"):
                    anonymization_identifier = member_info.get("email")
                break

    if author:
        # Get display identifier for author (use anonymization_identifier for consistent hash)
        display_author = get_identifier_for_display(
            anonymization_identifier, args.hide_individual_names
        )
        print_header("GitHub PR Analysis Report Generator", f"Author: {display_author}")
    else:
        print_header("GitHub PR Analysis Report Generator", "Team Overall Report")

    print()

    # Step 1: Cleanup old reports
    print(f"{Colors.YELLOW}Step 1: Cleaning up old files...{Colors.NC}")
    # Use anonymization_identifier for consistent file naming
    identifier = (
        normalize_username(anonymization_identifier) if anonymization_identifier else "general"
    )
    cleanup_old_reports(reports_dir, identifier, "pr")
    print()

    # Step 2-N: Generate metrics for each phase
    step_num = 2

    for phase_name, start_date, end_date in phases:
        print(
            f"{Colors.YELLOW}Step {step_num}: Collecting PR metrics for '{phase_name}' ({start_date} to {end_date})...{Colors.NC}"
        )

        success = generate_phase_metrics(
            phase_name,
            start_date,
            end_date,
            author=author,
            incremental=args.incremental,
            output_dir=str(reports_dir),
            hide_individual_names=args.hide_individual_names,
            config_file=config_file,
        )

        if success:
            print(f"{Colors.GREEN}  ✓ '{phase_name}' metrics collected{Colors.NC}")
        else:
            print(f"{Colors.RED}  ✗ Failed to collect '{phase_name}' metrics{Colors.NC}")
            return 1

        print()
        step_num += 1

    # Generate comparison report
    print(f"{Colors.YELLOW}Step {step_num}: Generating comparison report...{Colors.NC}")
    if not generate_comparison_report(
        author=author,
        output_dir=str(reports_dir),
        config_file=config_file,
        hide_individual_names=args.hide_individual_names,
    ):
        print(f"{Colors.RED}  ✗ Failed to generate comparison report{Colors.NC}")
        return 1
    print()

    # Find and upload the latest comparison report
    comparison_file = find_latest_comparison_report(reports_dir, identifier, "pr")
    if comparison_file:
        print(f"{Colors.GREEN}✓ Report generated: {comparison_file.name}{Colors.NC}")
        print()
        upload_to_google_sheets(comparison_file, skip_upload=args.no_upload)

    print(f"{Colors.GREEN}Done!{Colors.NC}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
