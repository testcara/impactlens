#!/usr/bin/env python3
"""
CLI script to fetch and analyze GitHub PR metrics.

This is a thin wrapper around the core business logic in
impactlens.core.pr_metrics_calculator
"""

import json
import os
import sys
import argparse
import traceback
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from impactlens.clients.github_client import GitHubClient
from impactlens.clients.github_client_graphql import GitHubGraphQLClient
from impactlens.core.pr_metrics_calculator import PRMetricsCalculator
from impactlens.core.pr_report_generator import PRReportGenerator
from impactlens.utils.logger import logger
from impactlens.utils.report_utils import get_identifier_for_display
from impactlens.utils.workflow_utils import load_team_members_from_yaml


def main():
    """Main entry point for PR metrics CLI."""
    parser = argparse.ArgumentParser(
        description="Collect GitHub PR metrics for AI impact analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Environment Variables:
  GITHUB_TOKEN       - GitHub personal access token (required)
  GITHUB_REPO_OWNER  - Repository owner/organization (required)
  GITHUB_REPO_NAME   - Repository name (required)

Examples:
  # Get PRs for October 2024
  python3 impactlens/scripts/get_pr_metrics.py --start 2024-10-01 --end 2024-10-31

  # Get PRs for specific author
  python3 impactlens/scripts/get_pr_metrics.py --start 2024-10-01 --end 2024-10-31 --author wlin

  # Custom output file
  python3 impactlens/scripts/get_pr_metrics.py --start 2024-10-01 --end 2024-10-31 --output my_report.json
        """,
    )

    parser.add_argument("--start", type=str, required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", type=str, required=True, help="End date (YYYY-MM-DD)")
    parser.add_argument("--author", type=str, help="Filter by PR author (GitHub username)")
    parser.add_argument(
        "--output", type=str, help="Output JSON file path (default: auto-generated)"
    )
    parser.add_argument(
        "--use-graphql",
        action="store_true",
        default=True,
        help="Use GraphQL API (faster, default: True)",
    )
    parser.add_argument(
        "--use-rest",
        action="store_true",
        help="Use REST API (legacy mode, slower)",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable caching (GraphQL only)",
    )
    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="Clear cache before fetching (GraphQL only)",
    )
    parser.add_argument(
        "--incremental",
        action="store_true",
        help="Incremental mode: only fetch PRs updated since last run (GraphQL only)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        help="Output directory for reports (default: reports/github)",
        default="reports/github",
    )
    parser.add_argument(
        "--hide-individual-names",
        action="store_true",
        help="Anonymize individual names in filenames (Developer-A3F2, etc.)",
    )
    parser.add_argument(
        "--config",
        type=str,
        help="Path to config file (for email lookup when anonymizing)",
    )

    args = parser.parse_args()

    # Validate dates
    try:
        datetime.strptime(args.start, "%Y-%m-%d")
        datetime.strptime(args.end, "%Y-%m-%d")
    except ValueError:
        print("Error: Dates must be in YYYY-MM-DD format")
        return 1

    # For anonymization consistency: use email if available, otherwise use author
    # This ensures the same person gets the same hash in both Jira and PR reports
    anonymization_identifier = args.author
    if args.author and args.config:
        # Try to find email for this author from config
        config_path = Path(args.config)
        if config_path.exists():
            members_detailed = load_team_members_from_yaml(config_path, detailed=True)
            for member_id, member_info in members_detailed.items():
                if member_info.get("name") == args.author:
                    # Found the member, use email for anonymization if available
                    if member_info.get("email"):
                        anonymization_identifier = member_info.get("email")
                    break

    print("\n📊 Collecting GitHub PR metrics...")
    print(f"Period: {args.start} to {args.end}")
    if args.author:
        display_author = get_identifier_for_display(
            anonymization_identifier, args.hide_individual_names
        )
        print(f"Author: {display_author}")

    # Determine which client to use
    use_rest = args.use_rest
    use_graphql = not use_rest

    if use_rest:
        print("🔄 Using REST API (legacy mode)")
    else:
        print("⚡ Using GraphQL API (optimized mode)")
        if not args.no_cache:
            print("💾 Caching enabled")
        if args.incremental:
            print("📈 Incremental mode enabled")

    # Initialize GitHub client
    try:
        if use_graphql:
            client = GitHubGraphQLClient()

            if args.clear_cache:
                print("\n🗑️  Clearing cache...")
                client.clear_cache()
        else:
            client = GitHubClient()
    except ValueError as e:
        print(f"\nError: {e}")
        print("\nPlease set the following environment variables:")
        print("  export GITHUB_TOKEN='your_token'")
        print("  export GITHUB_REPO_OWNER='owner'")
        print("  export GITHUB_REPO_NAME='repo'")
        return 1

    # Fetch merged PRs
    print("\n📥 Fetching merged PRs...")
    try:
        if use_graphql:
            prs_with_metrics = client.fetch_merged_prs_graphql(
                args.start,
                args.end,
                author=args.author,
                use_cache=not args.no_cache,
                incremental=args.incremental,
            )
            print(f"✓ Fetched and analyzed {len(prs_with_metrics)} PRs")
        else:
            # REST API: fetch PRs first, then analyze each one
            prs = client.fetch_merged_prs(args.start, args.end)

            if args.author:
                prs = [pr for pr in prs if pr["user"]["login"] == args.author]
                print(f"✓ Filtered to {len(prs)} PRs by author '{args.author}'")

            if not prs:
                print("\n⚠ No merged PRs found for the specified period")
                return 0

            # Get detailed metrics for each PR
            print(f"\n📈 Analyzing {len(prs)} PRs (using concurrent processing)...")
            prs_with_metrics = []

            def analyze_single_pr(pr):
                try:
                    return client.get_pr_detailed_metrics(pr)
                except Exception as e:
                    logger.error(f"Error analyzing PR #{pr['number']}: {e}")
                    return None

            max_workers = min(10, len(prs))

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_pr = {executor.submit(analyze_single_pr, pr): pr for pr in prs}

                completed = 0
                for future in as_completed(future_to_pr):
                    pr = future_to_pr[future]
                    completed += 1

                    try:
                        metrics = future.result()
                        if metrics:
                            prs_with_metrics.append(metrics)
                            print(
                                f"  ✓ [{completed}/{len(prs)}] PR #{pr['number']}: {pr['title'][:60]}"
                            )
                        else:
                            print(
                                f"  ✗ [{completed}/{len(prs)}] PR #{pr['number']}: Failed to analyze"
                            )
                    except Exception as e:
                        print(f"  ✗ [{completed}/{len(prs)}] PR #{pr['number']}: {e}")

            print(f"\n✓ Successfully analyzed {len(prs_with_metrics)}/{len(prs)} PRs")
    except Exception as e:
        print(f"Error fetching PRs: {e}")
        traceback.print_exc()
        return 1

    # Calculate statistics using core logic (even if no PRs found)
    if not prs_with_metrics:
        print("\n⚠ No merged PRs found for the specified period")
        print("📊 Generating report with empty metrics...")

    print("\n📊 Calculating statistics...")
    calculator = PRMetricsCalculator()
    stats = calculator.calculate_statistics(prs_with_metrics, args.start, args.end)

    # Generate reports using core logic
    report_gen = PRReportGenerator()
    # Use anonymization_identifier for consistent hash generation
    text_report = report_gen.generate_text_report(
        stats,
        prs_with_metrics,
        args.start,
        args.end,
        client.repo_owner,
        client.repo_name,
        anonymization_identifier,
        hide_individual_names=args.hide_individual_names,
    )

    # Prepare JSON output
    # Use anonymization_identifier for consistent hash generation
    output_data = report_gen.generate_json_output(
        stats,
        prs_with_metrics,
        args.start,
        args.end,
        client.repo_owner,
        client.repo_name,
        anonymization_identifier,
        hide_individual_names=args.hide_individual_names,
    )

    # Save outputs
    if args.output:
        json_file = args.output
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        txt_file = None
    else:
        # Use anonymization_identifier for consistent file naming
        json_file = report_gen.save_json_output(
            output_data,
            args.start,
            args.end,
            anonymization_identifier,
            output_dir=args.output_dir,
            hide_individual_names=args.hide_individual_names,
        )
        txt_file = report_gen.save_text_report(
            text_report,
            args.start,
            args.end,
            anonymization_identifier,
            output_dir=args.output_dir,
            hide_individual_names=args.hide_individual_names,
        )

    # Display report (author already anonymized if needed)
    print("\n" + text_report)

    print("\n✅ Analysis complete!")
    if not args.hide_individual_names:
        print(f"📄 JSON output: {json_file}")
        if txt_file:
            print(f"📄 Text report: {txt_file}")
    else:
        print(f"📄 Reports saved (filenames hidden for privacy)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
