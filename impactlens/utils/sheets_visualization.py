"""
Create Google Sheets visualization reports with embedded PNG charts.

This module creates a Google Sheet that displays PNG charts from github,
mimicking the HTML visualization report layout.
"""

import os
from typing import List, Dict, Optional
from pathlib import Path


def create_visualization_sheet(
    service,
    report_path: str,
    chart_github_links: List[Dict],
    spreadsheet_id: Optional[str] = None,
    sheet_name: Optional[str] = None,
    config_path: Optional[str] = None,
    replace_existing: bool = False,
) -> Dict[str, str]:
    """
    Create a Google Sheet with embedded PNG charts for visualization.

    Args:
        service: Google Sheets API service
        report_path: Path to the combined report TSV file
        chart_github_links: List of dicts with chart metadata and GitHub links
                           [{"name": "...", "embedUrl": "...", "webViewLink": "..."}, ...]
        spreadsheet_id: Existing spreadsheet ID (creates new if None)
        sheet_name: Name for the sheet tab (auto-generated if None)
        config_path: Config file path for extracting sheet prefix (optional)
        replace_existing: If True, delete old visualization sheets with same name but different timestamp

    Returns:
        Dict with:
        - spreadsheet_id: The spreadsheet ID
        - sheet_name: The created sheet name
        - url: URL to the spreadsheet
    """
    from impactlens.clients.sheets_client import (
        create_spreadsheet,
        get_existing_sheets,
        cleanup_old_sheets,
    )

    # Read report metadata
    with open(report_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Extract metadata
    project_name = ""
    generation_date = ""
    report_type = "Jira" if "jira" in report_path.lower() else "PR"

    for line in lines[:10]:
        if "Report" in line and "Generated:" in line:
            generation_date = line.split("Generated:", 1)[1].strip()
        elif "Repository:" in line or "Project:" in line:
            project_name = line.split(":", 1)[1].strip()

    # Generate sheet name (reuse the same logic as upload_to_sheets + "(Visual)" prefix)
    if sheet_name is None:
        from impactlens.utils.core_utils import generate_sheet_name_from_report

        # Generate base name using shared utility (ensures consistency with data sheet)
        base_name = generate_sheet_name_from_report(report_path, config_path=config_path)

        # Add "(Visual)" prefix to distinguish from data sheet
        sheet_name = f"(Visual) {base_name}"

    # Create or use existing spreadsheet
    if spreadsheet_id is None:
        title = (
            f"{project_name} - Visualization Reports" if project_name else "Visualization Reports"
        )
        spreadsheet_id = create_spreadsheet(service, title)
        print(f"✓ Created new spreadsheet: {spreadsheet_id}")
    else:
        print(f"✓ Using existing spreadsheet: {spreadsheet_id}")

    # Always add timestamp to sheet name (consistent with other sheets)
    import datetime

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    sheet_name = f"{sheet_name} - {timestamp}"

    # Create new sheet
    _create_sheet_tab(service, spreadsheet_id, sheet_name)

    # Get sheet ID once and cache it to avoid repeated API calls
    sheet_id = _get_sheet_id(service, spreadsheet_id, sheet_name)

    # Build sheet content
    requests = []

    # Add title row
    row_index = 0
    title_text = (
        f"{project_name} - {report_type} Visualization Report"
        if project_name
        else f"{report_type} Visualization Report"
    )

    requests.append(
        {
            "updateCells": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": row_index,
                    "endRowIndex": row_index + 1,
                    "startColumnIndex": 0,
                    "endColumnIndex": 1,
                },
                "rows": [
                    {
                        "values": [
                            {
                                "userEnteredValue": {"stringValue": title_text},
                                "userEnteredFormat": {
                                    "textFormat": {"fontSize": 18, "bold": True},
                                    "backgroundColor": {"red": 1, "green": 1, "blue": 1},
                                },
                            }
                        ]
                    }
                ],
                "fields": "userEnteredValue,userEnteredFormat",
            }
        }
    )
    row_index += 1

    # Add metadata (Generated date, Source report, Chart count)
    source_report_filename = os.path.basename(report_path)
    num_charts = len(chart_github_links)

    # Determine not-visualized metrics based on report type
    if report_type == "Jira":
        not_visualized = "Total Issues Completed, etc."
    else:  # PR
        not_visualized = "Total PRs Merged, Non-AI PRs, Claude/Cursor PRs, Total Lines/Files, etc."

    metadata_lines = []
    if generation_date:
        metadata_lines.append(f"Generated: {generation_date}")
    metadata_lines.append(f"Source Report: {source_report_filename}")
    metadata_lines.append(f"Visualized Metrics: {num_charts} charts")
    metadata_lines.append(
        f"Not visualized: {not_visualized} (cumulative/count metrics less suitable for distribution analysis)"
    )

    metadata_text = "\n".join(metadata_lines)

    # Metadata spans across 2 columns for more space
    requests.append(
        {
            "updateCells": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": row_index,
                    "endRowIndex": row_index + 1,
                    "startColumnIndex": 0,
                    "endColumnIndex": 1,
                },
                "rows": [
                    {
                        "values": [
                            {
                                "userEnteredValue": {"stringValue": metadata_text},
                                "userEnteredFormat": {
                                    "textFormat": {
                                        "fontSize": 10,
                                        "italic": True,
                                        "foregroundColor": {
                                            "red": 0.4,
                                            "green": 0.4,
                                            "blue": 0.4,
                                        },
                                    },
                                    "wrapStrategy": "WRAP",
                                },
                            }
                        ]
                    }
                ],
                "fields": "userEnteredValue,userEnteredFormat",
            }
        }
    )

    # Merge cells for metadata to span 2 columns
    requests.append(
        {
            "mergeCells": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": row_index,
                    "endRowIndex": row_index + 1,
                    "startColumnIndex": 0,
                    "endColumnIndex": 2,
                },
                "mergeType": "MERGE_ALL",
            }
        }
    )
    row_index += 1

    # Add guide section (2 columns: How to Read | Important Notes)
    row_index += 1
    guide_text = """📊 How to Read Box Plots:
• Box plots show the distribution of metrics across team members
• The box represents the middle 50% of values (25th to 75th percentile)
• The line inside the box is the median (50th percentile)
• Whiskers extend to show the range of typical values
• Dots beyond whiskers are outliers
• Red dashed line shows the team average"""

    notes_text = """⚠️ Important Notes:

Data Quality:
• Excludes N/A and team aggregated values from charts
• Box plots need 3+ members to be meaningful
• CI reports use anonymized IDs (e.g., Developer-A3F2)

Tips:
• Compare multiple metrics for complete insights
• Consider team changes and external factors"""

    # Add both columns side by side
    requests.append(
        {
            "updateCells": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": row_index,
                    "endRowIndex": row_index + 1,
                    "startColumnIndex": 0,
                    "endColumnIndex": 2,
                },
                "rows": [
                    {
                        "values": [
                            {
                                "userEnteredValue": {"stringValue": guide_text},
                                "userEnteredFormat": {
                                    "textFormat": {"fontSize": 9},
                                    "backgroundColor": {"red": 0.94, "green": 0.96, "blue": 1},
                                    "wrapStrategy": "WRAP",
                                    "verticalAlignment": "TOP",
                                },
                            },
                            {
                                "userEnteredValue": {"stringValue": notes_text},
                                "userEnteredFormat": {
                                    "textFormat": {"fontSize": 9},
                                    "backgroundColor": {"red": 1, "green": 0.95, "blue": 0.9},
                                    "wrapStrategy": "WRAP",
                                    "verticalAlignment": "TOP",
                                },
                            },
                        ]
                    }
                ],
                "fields": "userEnteredValue,userEnteredFormat",
            }
        }
    )
    row_index += 2

    # Add charts in 2-column layout (no titles, images have their own titles)
    num_columns = 2
    chart_height = 300  # Smaller height for better fit
    chart_width = 600  # Width per column

    for idx, chart_info in enumerate(chart_github_links):
        embed_url = chart_info["embedUrl"]

        # Calculate position (2 columns layout)
        col_index = idx % num_columns
        current_row = row_index + (idx // num_columns)

        # Add IMAGE formula
        requests.append(
            {
                "updateCells": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": current_row,
                        "endRowIndex": current_row + 1,
                        "startColumnIndex": col_index,
                        "endColumnIndex": col_index + 1,
                    },
                    "rows": [
                        {
                            "values": [
                                {
                                    "userEnteredValue": {
                                        "formulaValue": f'=IMAGE("{embed_url}", 4, {chart_height}, {chart_width})'
                                    },
                                }
                            ]
                        }
                    ],
                    "fields": "userEnteredValue",
                }
            }
        )

        # Set row height for this row (only once per row)
        if col_index == 0 or idx == 0:
            requests.append(
                {
                    "updateDimensionProperties": {
                        "range": {
                            "sheetId": sheet_id,
                            "dimension": "ROWS",
                            "startIndex": current_row,
                            "endIndex": current_row + 1,
                        },
                        "properties": {"pixelSize": chart_height},
                        "fields": "pixelSize",
                    }
                }
            )

    # Set column widths for both columns
    for col in range(num_columns):
        requests.append(
            {
                "updateDimensionProperties": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "COLUMNS",
                        "startIndex": col,
                        "endIndex": col + 1,
                    },
                    "properties": {"pixelSize": chart_width},
                    "fields": "pixelSize",
                }
            }
        )

    # Execute all requests
    if requests:
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id, body={"requests": requests}
        ).execute()

    spreadsheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"

    print(f"✅ Created visualization sheet: {sheet_name}")
    print(f"   📊 {len(chart_github_links)} charts embedded")
    print(f"   🔗 {spreadsheet_url}")

    # Delete old visualization sheets with same prefix if replace_existing is True
    if replace_existing:
        cleanup_old_sheets(
            service=service,
            spreadsheet_id=spreadsheet_id,
            new_sheet_name=sheet_name,
            reason="visualization replace_existing=True",
        )

    return {
        "spreadsheet_id": spreadsheet_id,
        "sheet_name": sheet_name,
        "url": spreadsheet_url,
    }


def _create_sheet_tab(service, spreadsheet_id: str, sheet_name: str) -> int:
    """Create a new sheet tab in the spreadsheet with auto-assigned color based on team name."""
    from impactlens.clients.sheets_client import get_sheet_properties_with_color

    # Get sheet properties with auto-assigned color
    properties = get_sheet_properties_with_color(sheet_name)
    request = {"addSheet": {"properties": properties}}

    response = (
        service.spreadsheets()
        .batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": [request]})
        .execute()
    )

    return response["replies"][0]["addSheet"]["properties"]["sheetId"]


def _get_sheet_id(service, spreadsheet_id: str, sheet_name: str) -> int:
    """Get the sheet ID from sheet name."""
    spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()

    for sheet in spreadsheet["sheets"]:
        if sheet["properties"]["title"] == sheet_name:
            return sheet["properties"]["sheetId"]

    raise ValueError(f"Sheet '{sheet_name}' not found")
