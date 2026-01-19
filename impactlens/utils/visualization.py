"""
Visualization utilities for generating charts from combined reports.

This module provides functions to generate box plots and line charts
to visualize team metrics trends across different phases.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import matplotlib

    matplotlib.use("Agg")  # Non-interactive backend for CI/server environments
    import matplotlib.pyplot as plt
    import numpy as np

    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("Warning: matplotlib not installed. Charts will not be generated.")
    print("Install with: pip install matplotlib")


def parse_combined_report_section(lines: List[str], section_name: str) -> Optional[Dict]:
    """
    Parse a section from combined report TSV format.

    Args:
        lines: List of lines from the TSV file
        section_name: Name of the section (e.g., "Daily Throughput")

    Returns:
        Dictionary with structure:
        {
            'phases': ['Phase 1', 'Phase 2', ...],
            'team': [val1, val2, ...],
            'members': {
                'Developer-1': [val1, val2, ...],
                'Developer-2': [val1, val2, ...],
            }
        }
        Returns None if section not found or parsing fails.
    """
    # Find section header
    section_header = f"=== {section_name} ==="
    try:
        # Try with newline first (most common)
        start_idx = lines.index(section_header + "\n")
    except ValueError:
        try:
            # Try without newline (in case it's the last line)
            start_idx = lines.index(section_header)
        except ValueError:
            return None

    # Parse column headers (Phase\tteam\tDeveloper-1\t...)
    header_line = lines[start_idx + 1]
    columns = header_line.strip().split("\t")

    if len(columns) < 2 or columns[0] != "Phase" or columns[1] != "team":
        return None

    member_names = columns[2:]  # All columns after 'team'

    # Parse data rows
    data = {"phases": [], "team": [], "members": {name: [] for name in member_names}}

    # Read until next section or end
    idx = start_idx + 2
    while idx < len(lines):
        line = lines[idx].strip()

        # Stop at next section or empty line
        if line.startswith("===") or line == "":
            break

        values = line.split("\t")
        if len(values) < 2:
            break

        phase_name = values[0]
        team_value = values[1]
        member_values = values[2:]

        data["phases"].append(phase_name)
        data["team"].append(_parse_value(team_value))

        for i, member_name in enumerate(member_names):
            if i < len(member_values):
                data["members"][member_name].append(_parse_value(member_values[i]))
            else:
                data["members"][member_name].append(None)

        idx += 1

    return data


def _parse_value(value_str: str) -> Optional[float]:
    """
    Parse a value from TSV (handles formats like '0.58/d', '12.5d', '50%', 'N/A').

    Returns:
        Float value or None if N/A or invalid
    """
    value_str = value_str.strip()

    if value_str == "N/A" or value_str == "":
        return None

    # Remove units: /d, d, %, h, x
    for unit in ["/d", "d", "%", "h", "x"]:
        value_str = value_str.replace(unit, "")

    try:
        return float(value_str)
    except ValueError:
        return None


def generate_boxplot(
    data: Dict, metric_name: str, output_path: str, unit: str = "", title_prefix: str = ""
) -> bool:
    """
    Generate box plot showing team member distribution across phases.

    Args:
        data: Parsed section data from parse_combined_report_section()
        metric_name: Name of the metric (e.g., "Daily Throughput")
        output_path: Path to save the chart (e.g., "reports/charts/throughput.png")
        unit: Unit string to display on Y-axis (e.g., "/d", "days", "%")
        title_prefix: Optional prefix for chart title (e.g., "Konflux UI - ")

    Returns:
        True if chart generated successfully, False otherwise
    """
    if not MATPLOTLIB_AVAILABLE:
        return False

    if not data or not data["phases"]:
        print(f"No data available for {metric_name}")
        return False

    # Prepare data for box plot
    phases = data["phases"]

    # Collect member values for each phase (excluding None values)
    member_distributions = []
    for phase_idx in range(len(phases)):
        phase_data = []
        for member_name, values in data["members"].items():
            if phase_idx < len(values) and values[phase_idx] is not None:
                phase_data.append(values[phase_idx])
        member_distributions.append(phase_data)

    # Create figure with single plot (smaller size for compact display)
    fig, ax = plt.subplots(1, 1, figsize=(8, 4.5))

    # === Box Plot ===
    bp = ax.boxplot(member_distributions, labels=phases, patch_artist=True)

    # Customize box plot colors
    for patch in bp["boxes"]:
        patch.set_facecolor("#93c5fd")  # Light blue
        patch.set_alpha(0.7)

    for whisker in bp["whiskers"]:
        whisker.set(color="#1e40af", linewidth=1.5)

    for cap in bp["caps"]:
        cap.set(color="#1e40af", linewidth=1.5)

    for median in bp["medians"]:
        median.set(color="#dc2626", linewidth=2)  # Red median line

    # Use metric name only (title_prefix already shown in HTML header)
    ax.set_title(f"{metric_name}", fontsize=14, fontweight="bold")
    ax.set_ylabel(f"{metric_name} ({unit})" if unit else metric_name, fontsize=12)
    ax.set_xlabel("Phase", fontsize=12)
    ax.grid(True, alpha=0.3, axis="y")
    ax.tick_params(axis="x", rotation=15)

    plt.tight_layout()

    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Save figure with high DPI for better quality in Google Sheets
    plt.savefig(output_path, dpi=95, bbox_inches="tight")
    plt.close()

    print(f"Chart saved: {output_path}")
    return True


def generate_html_visualization_report(
    report_path: str, chart_files: List[str], output_path: Optional[str] = None
) -> str:
    """
    Generate HTML visualization report combining all charts.

    Args:
        report_path: Path to combined report TSV file
        chart_files: List of generated chart PNG file paths
        output_path: Path to save HTML file. If None, uses same location as report_path

    Returns:
        Path to generated HTML file
    """
    import base64
    from datetime import datetime

    # Read report metadata
    with open(report_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Extract title and metadata
    report_title = "Combined Report Visualization"
    project_name = ""
    generation_date = datetime.now().strftime("%B %d, %Y")

    # Detect report type
    report_type = "Jira" if "jira" in report_path.lower() else "PR"

    for line in lines[:10]:
        if "Report" in line and "Generated:" in line:
            generation_date = line.split("Generated:", 1)[1].strip()
        elif "Repository:" in line or "Project:" in line:
            project_name = line.split(":", 1)[1].strip()
            report_title = f"{project_name} - {report_type} Visualization Report"

    # If no project name found, use generic title with type
    if not project_name:
        report_title = f"{report_type} Visualization Report"

    # Count actual metrics from report (count === sections)
    total_metrics = sum(
        1 for line in lines if line.strip().startswith("===") and line.strip().endswith("===")
    )

    # Prepare exclusion notes based on report type
    if report_type == "Jira":
        excluded_note = "Total Issues Completed, etc. (cumulative/count metrics less suitable for distribution analysis)"
    else:  # PR
        excluded_note = "Total PRs Merged, Non-AI PRs, Claude/Cursor PRs, Total Lines/Files, etc. (cumulative/count metrics less suitable for distribution analysis)"

    # Determine output path
    if output_path is None:
        report_dir = Path(report_path).parent
        report_name = Path(report_path).stem
        output_path = str(report_dir / f"{report_name}_visualization.html")

    # Generate HTML
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{report_title}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
            line-height: 1.6;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background-color: white;
            padding: 40px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            border-radius: 8px;
        }}
        h1 {{
            color: #1a1a1a;
            border-bottom: 3px solid #2563eb;
            padding-bottom: 10px;
            margin-bottom: 10px;
        }}
        h2 {{
            color: #2563eb;
            border-left: 4px solid #2563eb;
            padding-left: 15px;
            margin-top: 30px;
            margin-bottom: 20px;
        }}
        .metadata {{
            color: #666;
            margin-bottom: 20px;
            font-size: 14px;
        }}
        .metadata p {{
            margin: 5px 0;
        }}
        .info-row {{
            display: flex;
            gap: 20px;
            margin-bottom: 30px;
        }}
        .info-box {{
            flex: 1;
            padding: 20px;
            border-radius: 4px;
        }}
        .guide-section {{
            background-color: #eff6ff;
            border-left: 4px solid #2563eb;
        }}
        .guide-section h3 {{
            color: #1e40af;
            margin-top: 0;
            margin-bottom: 15px;
            font-size: 16px;
        }}
        .guide-section p {{
            margin: 8px 0;
            color: #374151;
            font-size: 14px;
        }}
        .guide-section ul {{
            margin: 8px 0;
            padding-left: 20px;
            color: #374151;
            font-size: 14px;
        }}
        .guide-section li {{
            margin: 5px 0;
        }}
        .guide-section strong {{
            color: #1e40af;
        }}
        .warning-box {{
            background-color: #fef3c7;
            border-left: 4px solid #f59e0b;
        }}
        .warning-box h3 {{
            color: #92400e;
            margin-top: 0;
            margin-bottom: 10px;
            font-size: 16px;
        }}
        .warning-box p {{
            margin: 5px 0;
            color: #78350f;
            font-size: 14px;
        }}
        .warning-box ul {{
            margin: 8px 0;
            padding-left: 20px;
            font-size: 13px;
        }}
        .warning-box li {{
            margin: 4px 0;
        }}
        @media (max-width: 768px) {{
            .info-row {{
                flex-direction: column;
            }}
        }}
        .charts-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 20px;
            margin-bottom: 30px;
        }}
        .chart-section {{
            page-break-inside: avoid;
        }}
        .chart-container {{
            background-color: #fafafa;
            padding: 10px;
            border-radius: 8px;
            text-align: center;
        }}
        .chart-container img {{
            max-width: 100%;
            height: auto;
            border-radius: 4px;
        }}
        @media (max-width: 900px) {{
            .charts-grid {{
                grid-template-columns: 1fr;
            }}
        }}
        .footer {{
            margin-top: 50px;
            padding-top: 20px;
            border-top: 1px solid #e0e0e0;
            text-align: center;
            color: #666;
            font-size: 14px;
        }}
        @media print {{
            body {{
                background-color: white;
            }}
            .container {{
                box-shadow: none;
                padding: 20px;
            }}
            .guide-section, .warning-box {{
                page-break-inside: avoid;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{report_title}</h1>
        <div class="metadata">
            <p><strong>Generated:</strong> {generation_date}</p>
            <p><strong>Source Report:</strong> {Path(report_path).name}</p>
            <p><strong>Data Source:</strong> Individual team members only (team aggregated column excluded)</p>
            <p><strong>Visualized Metrics:</strong> {len(chart_files)} out of {total_metrics} total metrics</p>
            <p style="font-size: 13px; color: #888; margin-top: 8px;">
                <strong>Not visualized:</strong> {excluded_note}
            </p>
        </div>

        <div class="info-row">
            <div class="info-box guide-section">
                <h3>📊 How to Read Box Plots</h3>
                <p><strong>Box:</strong> 50% of data (Q1-Q3) | <strong>Red Line:</strong> Median | <strong>Whiskers:</strong> Min-max range | <strong>Dots:</strong> Outliers</p>
                <p style="margin-top: 15px;"><strong>What to Look For:</strong></p>
                <ul style="margin-top: 8px;">
                    <li>📈 Higher median = Better (throughput)</li>
                    <li>📉 Lower median = Better (time)</li>
                    <li>📏 Narrow box = Consistent team</li>
                    <li>📐 Wide box = High variation</li>
                </ul>
            </div>

            <div class="info-box warning-box">
                <h3>⚠️ Important Notes</h3>
                <p><strong>Data Quality:</strong></p>
                <ul>
                    <li>Excludes N/A values from charts</li>
                    <li>Box plots need 3+ members to be meaningful</li>
                    <li>CI reports use anonymized IDs (e.g., Developer-A3F2)</li>
                </ul>
                <p><strong>Tips:</strong></p>
                <ul>
                    <li>Compare multiple metrics for complete insights</li>
                    <li>Consider team changes and external factors</li>
                </ul>
            </div>
        </div>

        <h2>📈 Metrics Visualization</h2>
        <div class="charts-grid">
"""

    # Add each chart as a section in grid
    for chart_path in chart_files:
        chart_name = Path(chart_path).stem.replace("_", " ").title()

        # Read image and encode as base64 (embed in HTML)
        with open(chart_path, "rb") as img_file:
            img_data = base64.b64encode(img_file.read()).decode("utf-8")

        html_content += f"""
            <div class="chart-section">
                <div class="chart-container">
                    <img src="data:image/png;base64,{img_data}" alt="{chart_name}">
                </div>
            </div>
"""

    # Close grid
    html_content += """
        </div>
"""

    # Add footer
    html_content += f"""
        <div class="footer">
            <p>Generated by ImpactLens | <a href="https://github.com/testcara/impactlens">GitHub</a></p>
            <p>For detailed metric explanations, see <a href="https://github.com/testcara/impactlens/blob/master/docs/METRICS_GUIDE.md">Metrics Guide</a></p>
        </div>
    </div>
</body>
</html>
"""

    # Write HTML file
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"\nHTML visualization report saved: {output_path}")
    return output_path


def generate_charts_from_combined_report(
    report_path: str,
    output_dir: str,
    metrics_config: Optional[List[Tuple[str, str]]] = None,
    create_sheets_visualization: bool = False,
    spreadsheet_id: Optional[str] = None,
    upload_charts_to_github: bool = True,
    github_repo: str = "testcara/impactlens-charts",
    team_name: Optional[str] = None,
    config_path: Optional[str] = None,
    replace_existing: bool = False,
) -> tuple[List[str], Optional[Dict]]:
    """
    Generate charts for all key metrics in a combined report.

    Args:
        report_path: Path to combined report TSV file
        output_dir: Directory to save generated charts
        metrics_config: List of (metric_name, unit) tuples to visualize
                       If None, auto-detects report type and uses default metrics
        create_sheets_visualization: If True, create Google Sheet with embedded charts
        spreadsheet_id: Existing spreadsheet ID for visualization sheet (creates new if None)
        upload_charts_to_github: If True, upload PNG charts to GitHub repository (default: True)
        github_repo: GitHub repository in format "owner/repo" (default: testcara/impactlens-charts)
        team_name: Team name for organizing charts in GitHub (auto-detected from report path if None)
        config_path: Config file path for extracting sheet prefix (optional)
        replace_existing: If True, delete old sheets with same name but different timestamp

    Returns:
        Tuple of:
        - List of generated chart file paths
        - Dict with visualization info (chart_github_urls, sheet_info) or None
    """
    if not MATPLOTLIB_AVAILABLE:
        print("matplotlib not available, skipping chart generation")
        return []

    # Auto-detect report type if metrics_config not provided
    if metrics_config is None:
        # Check if it's a Jira or PR report by looking at the filename or content
        is_jira_report = "jira" in report_path.lower()

        if is_jira_report:
            # Jira metrics (order matches combined report structure)
            metrics_config = [
                # Throughput metrics
                ("Daily Throughput (skip leave days)", "/d"),
                ("Daily Throughput (average per capacity)", "/d"),
                ("Daily Throughput (average per capacity, excl. leave)", "/d"),
                ("Daily Throughput", "/d"),
                # Closure time
                ("Average Closure Time", "days"),
                ("Longest Closure Time", "days"),
                # State times
                ("New State Avg Time", "days"),
                ("To Do State Avg Time", "days"),
                ("In Progress State Avg Time", "days"),
                ("Review State Avg Time", "days"),
                ("Release Pending State Avg Time", "days"),
                ("Waiting State Avg Time", "days"),
                # Re-entry rates
                ("To Do Re-entry Rate", "x"),
                ("In Progress Re-entry Rate", "x"),
                ("Review Re-entry Rate", "x"),
                ("Waiting Re-entry Rate", "x"),
                # Issue types
                ("Story Percentage", "%"),
                ("Task Percentage", "%"),
                ("Bug Percentage", "%"),
                ("Epic Percentage", "%"),
            ]
        else:
            # PR metrics (order matches combined report structure)
            metrics_config = [
                # Throughput metrics
                ("Daily Throughput (skip leave days)", "/d"),
                ("Daily Throughput (average per capacity)", "/d"),
                ("Daily Throughput (average per capacity, excl. leave)", "/d"),
                ("Daily Throughput", "/d"),
                # AI metrics
                ("AI Adoption Rate", "%"),
                ("AI-Assisted PRs", "PRs"),
                # Time metrics
                ("Avg Time to Merge per PR (days)", "days"),
                ("Avg Time to First Review per PR (hours)", "hours"),
                # Review metrics
                ("Avg Changes Requested per PR", "count"),
                ("Avg Commits per PR", "count"),
                ("Avg Reviewers per PR", "count"),
                ("Avg Comments per PR", "count"),
                # Code change metrics
                ("Avg Lines Added per PR", "lines"),
                ("Avg Lines Deleted per PR", "lines"),
                ("Avg Files Changed per PR", "files"),
            ]

    # Read report file
    try:
        with open(report_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"Report file not found: {report_path}")
        return []

    # Extract title prefix from report (e.g., "Konflux UI - ")
    title_prefix = ""
    for line in lines[:10]:
        if "Repository:" in line or "Project:" in line:
            title_prefix = line.split(":", 1)[1].strip() + " - "
            break

    generated_charts = []

    # Generate chart for each metric
    for metric_name, unit in metrics_config:
        data = parse_combined_report_section(lines, metric_name)

        if data is None:
            print(f"Metric not found in report: {metric_name}")
            continue

        # Create safe filename
        safe_name = metric_name.lower().replace(" ", "_").replace("(", "").replace(")", "")
        output_path = os.path.join(output_dir, f"{safe_name}.png")

        success = generate_boxplot(
            data=data,
            metric_name=metric_name,
            output_path=output_path,
            unit=unit,
            title_prefix=title_prefix,
        )

        if success:
            generated_charts.append(output_path)

    print(f"\nGenerated {len(generated_charts)} charts in {output_dir}")

    # Upload PNG charts to GitHub if requested
    chart_links = []
    github_urls = {}
    if upload_charts_to_github and generated_charts:
        try:
            from impactlens.utils.github_charts_uploader import (
                upload_charts_to_github as github_upload,
            )

            # Extract metadata from report path
            report_file = Path(report_path)

            # Determine report type
            report_type = "jira" if "jira" in report_path.lower() else "pr"

            # Auto-detect team name if not provided
            if team_name is None:
                # Extract team name from path (e.g., reports/test-ci-team1/jira/...)
                path_parts = report_file.parts
                team_name = "unknown"
                if "reports" in path_parts:
                    reports_idx = path_parts.index("reports")
                    if reports_idx + 1 < len(path_parts):
                        team_name = path_parts[reports_idx + 1]

            # Upload to GitHub
            github_urls = github_upload(
                chart_files=generated_charts,
                repo=github_repo,
                team_name=team_name,
                report_type=report_type,
            )

            # Build chart links for GitHub URLs
            for chart_path in generated_charts:
                filename = os.path.basename(chart_path)
                if filename in github_urls:
                    chart_links.append(
                        {
                            "path": chart_path,
                            "name": filename,
                            "embedUrl": github_urls[filename],
                            "webViewLink": github_urls[filename],
                        }
                    )

        except Exception as e:
            print(f"⚠️  Failed to upload charts to GitHub: {e}")

    # Create Google Sheets visualization if requested
    sheet_info = None
    if create_sheets_visualization and chart_links:
        try:
            from impactlens.clients.sheets_client import get_sheets_service
            from impactlens.utils.sheets_visualization import create_visualization_sheet

            print(f"\n📊 Creating Google Sheets visualization...")
            service = get_sheets_service()
            sheet_info = create_visualization_sheet(
                service=service,
                report_path=report_path,
                chart_github_links=chart_links,
                spreadsheet_id=spreadsheet_id,
                config_path=config_path,
                replace_existing=replace_existing,
            )
        except Exception as e:
            print(f"⚠️  Failed to create Sheets visualization: {e}")

    # Return results
    result_info = None
    if chart_links or sheet_info or github_urls:
        result_info = {
            "chart_github_links": chart_links,  # Chart links for Sheets visualization (GitHub URLs)
            "chart_github_urls": github_urls,  # Raw GitHub URLs dict
            "sheet_info": sheet_info,
        }

    return generated_charts, result_info
