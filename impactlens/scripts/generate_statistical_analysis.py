"""
Generate Box Plot Visualizations for PR Metrics

This script generates box plots for PR metrics across multiple phases
(e.g., No AI vs AI periods) to visualize distribution changes.

Usage:
    python -m impactlens.scripts.generate_statistical_analysis \
        --reports-dir reports/test-ci-team1/github \
        --phase-configs phase1:20241001_20241231:No_AI,phase2:20250101_20250107:AI \
        --output-dir reports/test-ci-team1/github/analysis

The script will:
1. Extract metric data from PR JSON reports
2. Generate box plots for 3 core metrics (Time to Merge, Time to First Review, Changes Requested)
3. Save plots as PNG files
4. Optionally upload to Google Sheets
"""

import argparse
import sys
import os
from pathlib import Path
from typing import List, Dict, Tuple
import json
from datetime import datetime

from impactlens.utils.logger import logger
from impactlens.utils.visualization import (
    extract_pr_data_from_json,
    generate_boxplot,
)


def parse_phase_configs(phase_config_str: str) -> List[Tuple[str, str, str]]:
    """
    Parse phase configuration string.

    Format: "name1:daterange1:label1,name2:daterange2:label2"
    Example: "phase1:20241001_20241231:No_AI,phase2:20250101_20250107:AI"

    Args:
        phase_config_str: Phase configuration string

    Returns:
        List of tuples: [(phase_name, date_range, label), ...]
    """
    phases = []
    for phase_str in phase_config_str.split(','):
        parts = phase_str.strip().split(':')
        if len(parts) != 3:
            logger.error(f"Invalid phase config format: {phase_str}")
            logger.error("Expected format: name:daterange:label")
            sys.exit(1)
        phases.append((parts[0], parts[1], parts[2]))
    return phases


def find_json_reports(reports_dir: Path, date_range: str) -> List[Path]:
    """
    Find PR metrics JSON files matching the date range.

    Args:
        reports_dir: Directory containing PR JSON reports
        date_range: Date range string (e.g., "20241001_20241231")

    Returns:
        List of matching JSON file paths
    """
    pattern = f"pr_metrics_*_{date_range}.json"
    matches = list(reports_dir.glob(pattern))
    logger.info(f"Found {len(matches)} JSON reports matching pattern: {pattern}")
    return matches


def main():
    parser = argparse.ArgumentParser(
        description="Generate statistical analysis and visualizations for PR metrics"
    )
    parser.add_argument(
        "--reports-dir",
        required=True,
        help="Directory containing PR JSON reports",
    )
    parser.add_argument(
        "--phase-configs",
        required=True,
        help='Phase configurations: "name1:daterange1:label1,name2:daterange2:label2"',
    )
    parser.add_argument(
        "--output-dir",
        help="Output directory for plots and analysis (default: reports-dir/analysis)",
    )
    parser.add_argument(
        "--upload",
        action="store_true",
        help="Upload plots to Google Sheets (requires GOOGLE_CREDENTIALS_FILE and GOOGLE_SPREADSHEET_ID)",
    )
    parser.add_argument(
        "--spreadsheet-id",
        help="Google Spreadsheet ID (default: from GOOGLE_SPREADSHEET_ID env var)",
    )
    parser.add_argument(
        "--sheet-name",
        default="Statistical Analysis",
        help="Google Sheet tab name (default: Statistical Analysis)",
    )
    args = parser.parse_args()

    # Parse inputs
    reports_dir = Path(args.reports_dir)
    if not reports_dir.exists():
        logger.error(f"Reports directory not found: {reports_dir}")
        sys.exit(1)

    phases = parse_phase_configs(args.phase_configs)

    output_dir = Path(args.output_dir) if args.output_dir else reports_dir / "analysis"
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 80)
    logger.info("Box Plot Visualization for PR Metrics")
    logger.info("=" * 80)
    logger.info(f"Reports directory: {reports_dir}")
    logger.info(f"Output directory: {output_dir}")
    logger.info(f"Phases: {len(phases)}")
    for phase_name, date_range, label in phases:
        logger.info(f"  - {phase_name}: {date_range} ({label})")
    logger.info("")

    # Core metrics to analyze
    metrics = [
        ("time_to_merge_hours", "Time to Merge", "hours"),
        ("time_to_first_review_hours", "Time to First Review", "hours"),
        ("changes_requested_count", "Changes Requested", "count"),
    ]

    # Process each metric
    for metric_key, metric_name, metric_unit in metrics:
        logger.info(f"Analyzing metric: {metric_name}")

        # Extract data for each phase
        phase_data = {}
        phase_labels = {}

        for phase_name, date_range, label in phases:
            json_files = find_json_reports(reports_dir, date_range)

            if not json_files:
                logger.warning(f"No JSON reports found for {phase_name} ({date_range})")
                phase_data[label] = []
                continue

            values = extract_pr_data_from_json(json_files, metric_key)
            phase_data[label] = values
            phase_labels[label] = phase_name

            logger.info(f"  {label}: {len(values)} data points from {len(json_files)} reports")

        # Skip if no data
        if not any(phase_data.values()):
            logger.warning(f"No data for {metric_name}, skipping")
            continue

        # Generate box plot
        plot_filename = f"{metric_key}_boxplot.png"
        plot_path = output_dir / plot_filename

        logger.info(f"  Generating box plot: {plot_path}")
        generate_boxplot(
            data_groups=phase_data,
            metric_name=metric_name,
            metric_unit=metric_unit,
            output_path=plot_path,
            title=f"{metric_name} Comparison Across Phases"
        )

        logger.info("")

    # Upload to Google Sheets if requested
    if args.upload:
        logger.info("=" * 80)
        logger.info("Uploading to Google Sheets")
        logger.info("=" * 80)

        try:
            import os
            from impactlens.clients.sheets_client import (
                get_credentials,
                build_service,
                create_new_sheet_tab,
                upload_image_to_sheet,
            )

            # Get spreadsheet ID
            spreadsheet_id = args.spreadsheet_id or os.getenv("GOOGLE_SPREADSHEET_ID")
            if not spreadsheet_id:
                logger.error("Error: No spreadsheet ID provided")
                logger.error("Set GOOGLE_SPREADSHEET_ID env var or use --spreadsheet-id")
                sys.exit(1)

            # Get credentials and build service
            credentials = get_credentials()
            service = build_service(credentials)

            # Create new sheet tab with timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            sheet_name = f"{args.sheet_name} - {timestamp}"

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
            import traceback
            traceback.print_exc()
            sys.exit(1)

    logger.info("=" * 80)
    logger.info("Box Plot Generation Complete")
    logger.info("=" * 80)
    logger.info(f"Output directory: {output_dir}")
    logger.info("Generated box plots:")
    for item in sorted(output_dir.iterdir()):
        if item.suffix == '.png':
            logger.info(f"  - {item.name}")
    logger.info("")


if __name__ == "__main__":
    main()
