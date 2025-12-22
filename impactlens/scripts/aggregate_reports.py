#!/usr/bin/env python3
"""
Aggregate Reports Script

Aggregates multiple combined reports (Jira/PR) into unified reports.
Reads already-generated TSV files and merges them based on aggregation config.
"""

import sys
import os
import argparse
from pathlib import Path

from impactlens.core.report_aggregator import ReportAggregator
from impactlens.utils.logger import logger, Colors, set_log_level
from impactlens.utils.workflow_utils import upload_to_google_sheets
from impactlens.utils.common_args import add_aggregate_reports_args


def main():
    """Main entry point for report aggregation."""
    parser = argparse.ArgumentParser(
        description="Aggregate multiple combined reports into unified reports",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Aggregate all reports (Jira + PR)
  %(prog)s --config config/aggregation_config.yaml

  # Aggregate only Jira reports
  %(prog)s --config config/aggregation_config.yaml --jira-only

  # Aggregate only PR reports
  %(prog)s --config config/aggregation_config.yaml --pr-only
        """,
    )

    add_aggregate_reports_args(parser)
    args = parser.parse_args()

    # Validate config file exists
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"{Colors.RED}Error: Config file not found: {config_path}{Colors.NC}")
        sys.exit(1)

    try:
        # Initialize aggregator
        aggregator = ReportAggregator(str(config_path))

        print(f"{Colors.GREEN}Starting report aggregation...{Colors.NC}")
        print(f"Config: {config_path}")
        print(f"Report name: {aggregator.name}")
        print(f"Output directory: {aggregator.output_dir}")
        print()

        results = {}

        # Determine what to aggregate
        aggregate_jira = not args.pr_only
        aggregate_pr = not args.jira_only

        # Aggregate Jira reports
        if aggregate_jira:
            print(f"{Colors.BLUE}Aggregating Jira reports...{Colors.NC}")
            jira_output = aggregator.aggregate_jira_reports()
            results["jira"] = jira_output

            if jira_output:
                print(f"{Colors.GREEN}✓ Jira aggregation complete: {jira_output}{Colors.NC}")
            else:
                print(f"{Colors.YELLOW}⚠ No Jira reports to aggregate{Colors.NC}")
            print()

        # Aggregate PR reports
        if aggregate_pr:
            print(f"{Colors.BLUE}Aggregating PR reports...{Colors.NC}")
            pr_output = aggregator.aggregate_pr_reports()
            results["pr"] = pr_output

            if pr_output:
                print(f"{Colors.GREEN}✓ PR aggregation complete: {pr_output}{Colors.NC}")
            else:
                print(f"{Colors.YELLOW}⚠ No PR reports to aggregate{Colors.NC}")
            print()

        # Upload aggregated reports to Google Sheets (if configured)
        print()
        print(f"{Colors.BLUE}Uploading aggregated reports to Google Sheets...{Colors.NC}")

        # Upload Jira aggregated report
        if results.get("jira"):
            upload_to_google_sheets(
                results["jira"], skip_upload=args.no_upload, config_path=config_path
            )

        # Upload PR aggregated report
        if results.get("pr"):
            upload_to_google_sheets(
                results["pr"], skip_upload=args.no_upload, config_path=config_path
            )

        # Summary
        print(f"{Colors.GREEN}{'='*80}{Colors.NC}")
        print(f"{Colors.GREEN}Report Aggregation Complete!{Colors.NC}")
        print(f"{Colors.GREEN}{'='*80}{Colors.NC}")

        if results.get("jira"):
            print(f"Jira Report: {results['jira']}")
        if results.get("pr"):
            print(f"PR Report: {results['pr']}")

        print(f"\nAll aggregated reports saved to: {aggregator.output_dir}")

    except FileNotFoundError as e:
        print(f"{Colors.RED}Error: {e}{Colors.NC}")
        sys.exit(1)
    except ValueError as e:
        print(f"{Colors.RED}Error: {e}{Colors.NC}")
        sys.exit(1)
    except Exception as e:
        logger.exception("Unexpected error during aggregation")
        print(f"{Colors.RED}Error: {e}{Colors.NC}")
        sys.exit(1)


if __name__ == "__main__":
    main()
