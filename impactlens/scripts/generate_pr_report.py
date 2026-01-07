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

from impactlens.utils.common_args import add_pr_report_args
from impactlens.utils.workflow_utils import (
    Colors,
    get_project_root,
    cleanup_old_reports,
    upload_to_google_sheets,
    find_latest_comparison_report,
    load_members_from_yaml,
    load_and_resolve_config,
    aggregate_member_values_for_phases,
)
from impactlens.utils.report_utils import (
    normalize_username,
    combine_comparison_reports,
    get_identifier_for_display,
    build_pr_project_prefix,
)
from impactlens.core.report_aggregator import ReportAggregator
from impactlens.utils.logger import logger


def print_header(title: str, subtitle: Optional[str] = None) -> None:
    """Print formatted header."""
    print(f"{Colors.BLUE}{'=' * 40}{Colors.NC}")
    print(f"{Colors.BLUE}{title}{Colors.NC}")
    if subtitle:
        print(f"{Colors.BLUE}{subtitle}{Colors.NC}")
    print(f"{Colors.BLUE}{'=' * 40}{Colors.NC}")
    print()


def generate_boxplots_from_config(
    config_file: Path,
    reports_dir: Path,
    phases: List[tuple],
    skip_upload: bool = False,
    project_settings: Optional[dict] = None,
) -> bool:
    """
    Generate box plot visualizations using config phases.

    Args:
        config_file: Path to PR config file (for Google Sheets ID)
        reports_dir: Directory containing PR JSON reports
        phases: List of (name, start_date, end_date) tuples from config
        skip_upload: If True, skip uploading to Google Sheets
        project_settings: Project settings from config (for sheet naming)

    Returns:
        True if successful, False otherwise
    """
    try:
        from datetime import datetime
        from impactlens.utils.visualization import extract_pr_data_from_json, generate_boxplot

        logger.info("=" * 80)
        logger.info("Generating Box Plot Visualizations")
        logger.info("=" * 80)

        # Create output directory
        output_dir = reports_dir / "box-plots"
        output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Output directory: {output_dir}")
        logger.info(f"Analyzing {len(phases)} phases:")
        for phase_name, start_date, end_date in phases:
            logger.info(f"  - {phase_name}: {start_date} to {end_date}")
        logger.info("")

        # Convert date formats for file matching (YYYY-MM-DD -> YYYYMMDD)
        def date_to_filename_format(date_str: str) -> str:
            """Convert YYYY-MM-DD to YYYYMMDD"""
            return date_str.replace("-", "")

        # Core metrics to visualize
        metrics = [
            ("time_to_merge_hours", "Time to Merge", "hours"),
            ("time_to_first_review_hours", "Time to First Review", "hours"),
            ("changes_requested_count", "Changes Requested", "count"),
        ]

        # Process each metric
        for metric_key, metric_name, metric_unit in metrics:
            logger.info(f"Generating box plot for: {metric_name}")

            # Extract data for each phase
            phase_data = {}
            for phase_name, start_date, end_date in phases:
                # Find JSON reports matching this phase
                start_fmt = date_to_filename_format(start_date)
                end_fmt = date_to_filename_format(end_date)
                date_range = f"{start_fmt}_{end_fmt}"

                # Pattern: pr_metrics_*_YYYYMMDD_YYYYMMDD.json
                pattern = f"pr_metrics_*_{date_range}.json"
                json_files = list(reports_dir.glob(pattern))

                if not json_files:
                    logger.warning(f"  No JSON reports found for {phase_name} (pattern: {pattern})")
                    phase_data[phase_name] = []
                    continue

                # Extract metric values
                values = extract_pr_data_from_json(json_files, metric_key)
                phase_data[phase_name] = values
                logger.info(f"  {phase_name}: {len(values)} data points from {len(json_files)} reports")

            # Skip if no data
            if not any(phase_data.values()):
                logger.warning(f"  No data for {metric_name}, skipping")
                continue

            # Generate box plot
            plot_filename = f"{metric_key}_boxplot.png"
            plot_path = output_dir / plot_filename

            generate_boxplot(
                data_groups=phase_data,
                metric_name=metric_name,
                metric_unit=metric_unit,
                output_path=plot_path,
                title=f"{metric_name} Comparison Across Phases"
            )

            logger.info(f"  ✓ Box plot saved: {plot_filename}")
            logger.info("")

        # Upload to Google Sheets if requested
        if not skip_upload:
            logger.info("=" * 80)
            logger.info("Uploading Box Plots to Google Sheets")
            logger.info("=" * 80)

            try:
                import os
                from impactlens.clients.sheets_client import (
                    get_credentials,
                    build_service,
                    create_new_sheet_tab,
                    upload_image_to_sheet,
                    get_spreadsheet_id,
                )

                # Get spreadsheet ID
                spreadsheet_id = get_spreadsheet_id(config_file)
                if not spreadsheet_id:
                    logger.warning("No spreadsheet ID configured, skipping upload")
                    return True

                # Get credentials and build service
                credentials = get_credentials()
                service = build_service(credentials)

                # Create sheet name with project info and timestamp
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
                if project_settings:
                    repo_owner = project_settings.get("github_repo_owner") or project_settings.get("gitlab_repo_owner", "unknown")
                    repo_name = project_settings.get("github_repo_name") or project_settings.get("gitlab_repo_name", "unknown")
                    sheet_name = f"Box Plots - {repo_owner}/{repo_name} - {timestamp}"
                else:
                    sheet_name = f"Box Plots - {timestamp}"

                logger.info(f"Creating sheet tab: {sheet_name}")
                create_new_sheet_tab(service, spreadsheet_id, sheet_name)

                # Upload plots
                plot_files = sorted([f for f in output_dir.iterdir() if f.suffix == '.png'])
                row = 0
                for plot_file in plot_files:
                    logger.info(f"Uploading: {plot_file.name}")
                    upload_image_to_sheet(
                        service,
                        spreadsheet_id,
                        str(plot_file),
                        sheet_name,
                        row=row,
                        col=0,
                        width=600,
                        height=400
                    )
                    row += 25  # Move to next row (leave space for image)

                logger.info(f"✓ Uploaded {len(plot_files)} plots to Google Sheets")
                logger.info(f"View at: https://docs.google.com/spreadsheets/d/{spreadsheet_id}")

            except Exception as e:
                logger.error(f"Failed to upload to Google Sheets: {e}")
                traceback.print_exc()
                # Don't fail the whole process if upload fails

        logger.info("=" * 80)
        logger.info("✓ Box Plot Generation Complete")
        logger.info("=" * 80)
        logger.info(f"Output directory: {output_dir}")
        logger.info("Generated plots:")
        for item in sorted(output_dir.iterdir()):
            if item.suffix == '.png':
                logger.info(f"  - {item.name}")
        logger.info("")

        return True

    except Exception as e:
        logger.error(f"Failed to generate box plots: {e}")
        traceback.print_exc()
        return False


def generate_phase_metrics(
    phase_name: str,
    start_date: str,
    end_date: str,
    author: Optional[str] = None,
    incremental: bool = False,
    output_dir: Optional[str] = None,
    hide_individual_names: bool = False,
    config_file: Optional[Path] = None,
    leave_days: float = 0,
    capacity: float = 1.0,
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

    if leave_days > 0:
        args.extend(["--leave-days", str(leave_days)])

    if capacity != 1.0:
        args.extend(["--capacity", str(capacity)])

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
    members_file: Path,
    script_name: str,
    no_upload: bool = False,
    upload_members: bool = False,
    config_file: Optional[Path] = None,
    hide_individual_names: bool = False,
) -> int:
    """
    Generate reports for all team members.

    Args:
        members_file: Path to config file with team members
        script_name: Script module name to invoke
        no_upload: If True, skip all uploads
        upload_members: If True, upload member reports (default: False, only team report is uploaded)
        config_file: Optional custom config file path
        hide_individual_names: If True, anonymize individual names in reports
    """
    print_header("Generating reports for all team members")

    # Load detailed member information (includes both name and email)
    members_detailed = load_members_from_yaml(members_file)
    if not members_detailed:
        print(f"{Colors.RED}Error: No team members found in {members_file}{Colors.NC}")
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
        github_username = member_info.get("github_username") or member_id
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

    parser = argparse.ArgumentParser(...)
    add_pr_report_args(parser)
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
            upload_to_google_sheets(
                output_file, skip_upload=args.no_upload, config_path=custom_config_file
            )

            print()
            print(f"{Colors.GREEN}{'=' * 40}{Colors.NC}")
            print(f"{Colors.GREEN}✓ Combined report completed successfully!{Colors.NC}")
            print(f"{Colors.GREEN}{'=' * 40}{Colors.NC}")

        except Exception as e:
            print(f"{Colors.RED}Error combining reports: {e}{Colors.NC}")
            return 1

        # Generate box plots if requested
        if args.generate_boxplot:
            print()
            print(f"{Colors.BLUE}{'=' * 40}{Colors.NC}")
            print(f"{Colors.BLUE}Generating box plot visualizations...{Colors.NC}")
            print(f"{Colors.BLUE}{'=' * 40}{Colors.NC}")
            print()
            try:
                success = generate_boxplots_from_config(
                    config_file=config_file,
                    reports_dir=reports_dir,
                    phases=phases,
                    skip_upload=args.no_upload,
                    project_settings=project_settings,
                )
                if success:
                    print(f"{Colors.GREEN}✓ Box plots generated successfully{Colors.NC}")
                else:
                    print(f"{Colors.YELLOW}⚠ Box plot generation had issues (check logs){Colors.NC}")
            except Exception as e:
                print(f"{Colors.RED}Error generating box plots: {e}{Colors.NC}")
                traceback.print_exc()
                # Don't fail the whole script if box plot generation fails

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
        members_detailed = load_members_from_yaml(config_file)
        for member_id, member_info in members_detailed.items():
            if member_info.get("github_username") == author:
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

    # Load leave_days and capacity from team members (using shared utility)
    leave_days_list, capacity_list = aggregate_member_values_for_phases(
        config_file, phases, author=author
    )

    # Step 2-N: Generate metrics for each phase
    step_num = 2

    for phase_index, (phase_name, start_date, end_date) in enumerate(phases):
        print(
            f"{Colors.YELLOW}Step {step_num}: Collecting PR metrics for '{phase_name}' ({start_date} to {end_date})...{Colors.NC}"
        )

        # Get leave_days for this phase
        phase_leave_days = 0
        if leave_days_list and phase_index < len(leave_days_list):
            phase_leave_days = leave_days_list[phase_index]

        # Get capacity for this phase
        phase_capacity = 1.0
        if capacity_list and phase_index < len(capacity_list):
            phase_capacity = capacity_list[phase_index]

        success = generate_phase_metrics(
            phase_name,
            start_date,
            end_date,
            author=author,
            incremental=args.incremental,
            output_dir=str(reports_dir),
            hide_individual_names=args.hide_individual_names,
            config_file=config_file,
            leave_days=phase_leave_days,
            capacity=phase_capacity,
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
        upload_to_google_sheets(
            comparison_file, skip_upload=args.no_upload, config_path=custom_config_file
        )

    print(f"{Colors.GREEN}Done!{Colors.NC}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
