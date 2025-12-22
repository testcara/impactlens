#!/usr/bin/env python3
"""
Clear all data from a Google Spreadsheet.

This script removes all sheets (tabs) from a Google Spreadsheet except the first one,
and optionally clears the content of the first sheet.

Usage:
    # Clear all sheets except the first one
    python -m impactlens.scripts.clear_google_sheets --spreadsheet-id YOUR_ID

    # Clear all sheets AND clear content of the first sheet
    python -m impactlens.scripts.clear_google_sheets --spreadsheet-id YOUR_ID --clear-first-sheet

    # Use environment variable for spreadsheet ID
    export GOOGLE_SPREADSHEET_ID="YOUR_ID"
    python -m impactlens.scripts.clear_google_sheets

    # Clear with custom credentials
    python -m impactlens.scripts.clear_google_sheets --credentials /path/to/creds.json
"""

import os
import sys
import argparse
import time
from pathlib import Path

# Add parent directory to path to allow imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from impactlens.clients.sheets_client import get_credentials, build_service
from impactlens.utils.logger import logger, Colors


def get_all_sheets(service, spreadsheet_id: str):
    """Get all sheets (tabs) in the spreadsheet."""
    try:
        spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        sheets = spreadsheet.get("sheets", [])
        return sheets
    except Exception as e:
        logger.error(f"Failed to get sheets: {e}")
        return []


def delete_sheet(service, spreadsheet_id: str, sheet_id: int):
    """Delete a specific sheet by its ID."""
    try:
        request_body = {"requests": [{"deleteSheet": {"sheetId": sheet_id}}]}
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id, body=request_body
        ).execute()
        return True
    except Exception as e:
        logger.error(f"Failed to delete sheet {sheet_id}: {e}")
        return False


def clear_sheet_content(service, spreadsheet_id: str, sheet_name: str):
    """Clear all content from a specific sheet."""
    try:
        # Clear all data in the sheet
        range_name = f"'{sheet_name}'!A1:ZZZ10000"
        service.spreadsheets().values().clear(
            spreadsheetId=spreadsheet_id, range=range_name
        ).execute()
        return True
    except Exception as e:
        logger.error(f"Failed to clear sheet '{sheet_name}': {e}")
        return False


def rename_sheet(service, spreadsheet_id: str, sheet_id: int, new_name: str):
    """Rename a sheet."""
    try:
        request_body = {
            "requests": [
                {
                    "updateSheetProperties": {
                        "properties": {"sheetId": sheet_id, "title": new_name},
                        "fields": "title",
                    }
                }
            ]
        }
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id, body=request_body
        ).execute()
        return True
    except Exception as e:
        logger.error(f"Failed to rename sheet: {e}")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Clear all data from a Google Spreadsheet",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Clear all sheets except the first one
  python -m impactlens.scripts.clear_google_sheets --spreadsheet-id 1ABCdef...

  # Clear all sheets AND clear content of the first sheet
  python -m impactlens.scripts.clear_google_sheets --spreadsheet-id 1ABCdef... --clear-first-sheet

  # Use environment variable
  export GOOGLE_SPREADSHEET_ID="1ABCdef..."
  python -m impactlens.scripts.clear_google_sheets

Environment Variables:
  GOOGLE_CREDENTIALS_FILE - Path to Google credentials JSON file (required)
  GOOGLE_SPREADSHEET_ID   - Default spreadsheet ID (can be overridden with --spreadsheet-id)

Note:
  This action is DESTRUCTIVE and cannot be undone!
  All sheets (tabs) except the first one will be permanently deleted.
        """,
    )

    parser.add_argument(
        "--spreadsheet-id",
        type=str,
        help="Google Spreadsheet ID (or set GOOGLE_SPREADSHEET_ID env var)",
        default=None,
    )
    parser.add_argument(
        "--credentials",
        type=str,
        help="Path to Google credentials JSON file (or set GOOGLE_CREDENTIALS_FILE env var)",
        default=None,
    )
    parser.add_argument(
        "--clear-first-sheet",
        action="store_true",
        help="Also clear content from the first sheet (default: keep first sheet with data)",
    )
    parser.add_argument(
        "--rename-first-sheet",
        type=str,
        help="Rename the first sheet to this name (e.g., 'Main')",
        default=None,
    )
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Skip confirmation prompt",
    )

    args = parser.parse_args()

    # Get spreadsheet ID from args or environment
    spreadsheet_id = args.spreadsheet_id or os.getenv("GOOGLE_SPREADSHEET_ID")
    if not spreadsheet_id:
        logger.error("Error: Spreadsheet ID not provided")
        logger.info("Provide --spreadsheet-id or set GOOGLE_SPREADSHEET_ID environment variable")
        return 1

    # Get credentials path
    credentials_path = args.credentials or os.getenv("GOOGLE_CREDENTIALS_FILE")
    if not credentials_path:
        logger.error("Error: Google credentials not provided")
        logger.info("Provide --credentials or set GOOGLE_CREDENTIALS_FILE environment variable")
        return 1

    if not Path(credentials_path).exists():
        logger.error(f"Error: Credentials file not found: {credentials_path}")
        return 1

    print(f"\n{Colors.YELLOW}{'='*60}{Colors.NC}")
    print(f"{Colors.YELLOW}Google Sheets Cleaner{Colors.NC}")
    print(f"{Colors.YELLOW}{'='*60}{Colors.NC}\n")

    # Build service
    try:
        creds = get_credentials(credentials_path)
        service = build_service(creds)
    except Exception as e:
        logger.error(f"Failed to connect to Google Sheets: {e}")
        return 1

    # Get all sheets
    sheets = get_all_sheets(service, spreadsheet_id)
    if not sheets:
        logger.error("No sheets found or failed to access spreadsheet")
        return 1

    print(f"{Colors.BLUE}Spreadsheet ID: {spreadsheet_id}{Colors.NC}")
    print(f"{Colors.BLUE}Total sheets: {len(sheets)}{Colors.NC}\n")

    # List all sheets
    print(f"{Colors.BLUE}Current sheets:{Colors.NC}")
    for i, sheet in enumerate(sheets, 1):
        sheet_title = sheet["properties"]["title"]
        sheet_id = sheet["properties"]["sheetId"]
        marker = " (will be kept)" if i == 1 else f" {Colors.RED}(will be deleted){Colors.NC}"
        print(f"  {i}. {sheet_title} (ID: {sheet_id}){marker}")

    if len(sheets) == 1:
        if args.clear_first_sheet:
            print(f"\n{Colors.YELLOW}Only one sheet exists. Will clear its content.{Colors.NC}")
        else:
            print(
                f"\n{Colors.YELLOW}Only one sheet exists and --clear-first-sheet not specified.{Colors.NC}"
            )
            print(f"{Colors.YELLOW}Nothing to do.{Colors.NC}")
            return 0

    # Confirmation
    if not args.yes:
        print(f"\n{Colors.RED}{'!'*60}{Colors.NC}")
        print(f"{Colors.RED}WARNING: This action is DESTRUCTIVE and cannot be undone!{Colors.NC}")
        print(f"{Colors.RED}{'!'*60}{Colors.NC}\n")

        if len(sheets) > 1:
            print(f"This will DELETE {len(sheets) - 1} sheet(s):")
            for sheet in sheets[1:]:
                print(f"  - {sheet['properties']['title']}")

        if args.clear_first_sheet:
            print(
                f"\nThe first sheet '{sheets[0]['properties']['title']}' will be CLEARED (content removed)"
            )

        print()
        response = (
            input(f"{Colors.YELLOW}Are you sure you want to proceed? (yes/no): {Colors.NC}")
            .strip()
            .lower()
        )
        if response not in ["yes", "y"]:
            print(f"{Colors.GREEN}Operation cancelled.{Colors.NC}")
            return 0

    print()

    # Delete all sheets except the first one
    deleted_count = 0
    failed_count = 0

    if len(sheets) > 1:
        print(f"{Colors.BLUE}Deleting sheets...{Colors.NC}")
        for i, sheet in enumerate(sheets[1:]):
            sheet_title = sheet["properties"]["title"]
            sheet_id = sheet["properties"]["sheetId"]

            if delete_sheet(service, spreadsheet_id, sheet_id):
                print(f"  {Colors.GREEN}✓{Colors.NC} Deleted: {sheet_title}")
                deleted_count += 1
            else:
                print(f"  {Colors.RED}✗{Colors.NC} Failed: {sheet_title}")
                failed_count += 1

            # Add delay to avoid rate limits (60 write requests per minute)
            # Sleep for 1.1 seconds between deletions (allows ~54 deletions/minute)
            if i < len(sheets) - 2:  # Don't sleep after the last deletion
                time.sleep(1.1)

    # Clear first sheet if requested
    if args.clear_first_sheet:
        first_sheet_name = sheets[0]["properties"]["title"]
        print(f"\n{Colors.BLUE}Clearing first sheet content...{Colors.NC}")
        if clear_sheet_content(service, spreadsheet_id, first_sheet_name):
            print(f"  {Colors.GREEN}✓{Colors.NC} Cleared: {first_sheet_name}")
        else:
            print(f"  {Colors.RED}✗{Colors.NC} Failed to clear: {first_sheet_name}")
            failed_count += 1

    # Rename first sheet if requested
    if args.rename_first_sheet:
        first_sheet_id = sheets[0]["properties"]["sheetId"]
        print(f"\n{Colors.BLUE}Renaming first sheet...{Colors.NC}")
        if rename_sheet(service, spreadsheet_id, first_sheet_id, args.rename_first_sheet):
            print(f"  {Colors.GREEN}✓{Colors.NC} Renamed to: {args.rename_first_sheet}")
        else:
            print(f"  {Colors.RED}✗{Colors.NC} Failed to rename")
            failed_count += 1

    # Summary
    print(f"\n{Colors.YELLOW}{'='*60}{Colors.NC}")
    print(f"{Colors.GREEN}Summary:{Colors.NC}")
    if deleted_count > 0:
        print(f"  Sheets deleted: {deleted_count}")
    if args.clear_first_sheet:
        print(f"  First sheet cleared: {'Yes' if failed_count == 0 else 'Failed'}")
    if failed_count > 0:
        print(f"  {Colors.RED}Failed operations: {failed_count}{Colors.NC}")
    else:
        print(f"  {Colors.GREEN}All operations completed successfully!{Colors.NC}")
    print(f"{Colors.YELLOW}{'='*60}{Colors.NC}\n")

    return 1 if failed_count > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
