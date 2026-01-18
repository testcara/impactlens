"""
Generate charts from combined reports.

This script reads combined report TSV files and generates box plots and line charts
for key metrics to visualize team trends across different phases.
"""

import argparse
import os
from pathlib import Path

from impactlens.utils.visualization import generate_charts_from_combined_report


def main():
    """
    CLI entry point for generating charts.

    Usage:
        python -m impactlens.scripts.generate_charts <report_path> [options]

    Example:
        python -m impactlens.scripts.generate_charts \\
            reports/test-ci-team1/github/combined_pr_report_20260107_154220.tsv \\
            --create-sheets-viz \\
            --spreadsheet-id 1ABCdef...
    """
    parser = argparse.ArgumentParser(description="Generate charts from combined reports")
    parser.add_argument("report_path", help="Path to combined report TSV file")
    parser.add_argument("output_dir", nargs="?", help="Output directory for charts (optional)")
    parser.add_argument(
        "--create-sheets-viz",
        action="store_true",
        help="Create Google Sheets visualization with embedded charts",
    )
    parser.add_argument(
        "--spreadsheet-id",
        help="Existing spreadsheet ID for visualization (creates new if not specified)",
    )

    args = parser.parse_args()

    # Default output directory: same as report file (parent directory)
    if args.output_dir:
        output_dir = args.output_dir
    else:
        output_dir = str(Path(args.report_path).parent)

    print(f"Generating charts from: {args.report_path}")
    print(f"Output directory: {output_dir}\n")

    # Get spreadsheet ID from args or environment
    spreadsheet_id = args.spreadsheet_id or os.environ.get("GOOGLE_SPREADSHEET_ID")

    generated_charts, result_info = generate_charts_from_combined_report(
        report_path=args.report_path,
        output_dir=output_dir,
        create_sheets_visualization=args.create_sheets_viz,
        spreadsheet_id=spreadsheet_id,
    )

    if generated_charts:
        print(f"\n✅ Success! Generated {len(generated_charts)} charts:")
        for chart_path in generated_charts:
            print(f"  - {chart_path}")

        if result_info:
            if result_info.get("chart_github_links"):
                print(f"\n📤 Uploaded {len(result_info['chart_github_links'])} charts to GitHub")

            if result_info.get("sheet_info"):
                sheet_info = result_info["sheet_info"]
                print(f"\n📊 Created visualization sheet:")
                print(f"   Sheet: {sheet_info['sheet_name']}")
                print(f"   URL: {sheet_info['url']}")
    else:
        print("\n❌ No charts were generated. Check the report file and metrics configuration.")
        return 1

    return 0


if __name__ == "__main__":
    main()
