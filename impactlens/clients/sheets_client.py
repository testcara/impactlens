"""
Google Sheets Client Library.

This module provides a client library for interacting with Google Sheets API.
It supports uploading data, creating spreadsheets, and formatting sheets.

Requirements:
    pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client

Setup:
    1. Create Service Account at https://console.cloud.google.com
       - Create project and enable Google Sheets API
       - Create Service Account credentials
       - Download JSON key file

    2. Set environment variable:
       export GOOGLE_CREDENTIALS_FILE=/path/to/service-account-key.json
"""

import os
import sys
from datetime import datetime

try:
    from google.oauth2 import service_account
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError as e:
    raise ImportError(
        "Google Sheets API libraries not installed. "
        "Install with: pip install -e . "
        "or: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client"
    ) from e


# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def get_credentials(credentials_file=None, token_file="tmp/google_sheets_token.json"):
    """
    Get Google Sheets API credentials.

    Supports two authentication methods:
    1. Service Account (for automated/server use)
    2. OAuth 2.0 (for interactive use)

    Args:
        credentials_file: Path to credentials JSON file
        token_file: Path to store OAuth token

    Returns:
        Credentials object
    """
    creds = None

    if not credentials_file:
        credentials_file = os.getenv("GOOGLE_CREDENTIALS_FILE")

    if not credentials_file:
        print("❌ Error: Google credentials file path not specified.")
        print("\nℹ️  Google Sheets upload requires authentication.")
        print("\nSetup instructions:")
        print("1. Go to https://console.cloud.google.com")
        print("2. Create a project and enable Google Sheets API")
        print("3. Create credentials (Service Account or OAuth 2.0)")
        print("4. Download the JSON file")
        print("5. Set environment variable:")
        print("   export GOOGLE_CREDENTIALS_FILE=/path/to/credentials.json")
        print("\nOr use --credentials flag:")
        print(
            "   python3 scripts/upload_to_sheets.py --credentials /path/to/credentials.json --report report.tsv"
        )
        sys.exit(1)

    if not os.path.exists(credentials_file):
        print(f"❌ Error: Google credentials file not found: {credentials_file}")
        print(f"\nℹ️  The specified credentials file does not exist.")
        print("\nPossible causes:")
        print("  • File path is incorrect")
        print("  • File was not created properly")
        print("  • In CI/CD: GOOGLE_CREDENTIALS_BASE64 secret may be missing or invalid")
        print("\nTo fix:")
        print("  • Verify the file exists at the specified path")
        print("  • Check that GOOGLE_CREDENTIALS_FILE environment variable is correct")
        print("  • In GitHub Actions: Ensure GOOGLE_CREDENTIALS_BASE64 secret is set")
        sys.exit(1)

    # Try Service Account first
    try:
        creds = service_account.Credentials.from_service_account_file(
            credentials_file, scopes=SCOPES
        )
        print("✓ Using Service Account authentication")
        return creds
    except ValueError as e:
        print(f"❌ Error: Invalid service account credentials file: {credentials_file}")
        print(f"   Details: {e}")
        print("\nℹ️  The credentials file appears to be corrupted or invalid.")
        print("   • Verify the file contains valid JSON")
        print("   • Re-download the credentials from Google Cloud Console")
        print("   • In CI/CD: Check that GOOGLE_CREDENTIALS_BASE64 is correctly base64-encoded")
        sys.exit(1)
    except Exception as e:
        # Not a service account file, try OAuth 2.0 flow
        print(f"Note: Not a service account file ({e}), trying OAuth 2.0...")

    # Fall back to OAuth 2.0
    # The token.json stores the user's access and refresh tokens
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
            creds = flow.run_local_server(port=0)

        # Save the credentials for the next run
        os.makedirs(os.path.dirname(token_file), exist_ok=True)
        with open(token_file, "w") as token:
            token.write(creds.to_json())
        print(f"✓ Using OAuth 2.0 authentication (token saved to {token_file})")

    return creds


def create_spreadsheet(service, title):
    """
    Create a new Google Spreadsheet.

    Args:
        service: Google Sheets API service
        title: Title for the spreadsheet

    Returns:
        Spreadsheet ID
    """
    spreadsheet = {"properties": {"title": title}}

    spreadsheet = service.spreadsheets().create(body=spreadsheet, fields="spreadsheetId").execute()

    return spreadsheet.get("spreadsheetId")


def get_existing_sheets(service, spreadsheet_id):
    """
    Get list of existing sheet names in a spreadsheet.

    Args:
        service: Google Sheets API service
        spreadsheet_id: ID of the spreadsheet

    Returns:
        List of sheet names

    Raises:
        HttpError: If the spreadsheet doesn't exist or the service account lacks permission
    """
    try:
        spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()

        sheets = spreadsheet.get("sheets", [])
        return [sheet["properties"]["title"] for sheet in sheets]
    except HttpError as e:
        if e.resp.status == 404:
            raise ValueError(
                f"Spreadsheet not found: {spreadsheet_id}\n"
                "Please check the GOOGLE_SPREADSHEET_ID environment variable."
            )
        elif e.resp.status == 403:
            raise ValueError(
                f"Permission denied for spreadsheet: {spreadsheet_id}\n"
                "If using a service account, share the spreadsheet with the service account email.\n"
                "Service account email is found in the 'client_email' field of your credentials JSON."
            )
        else:
            raise


def cleanup_old_sheets(service, spreadsheet_id, new_sheet_name, reason="cleanup requested"):
    """
    Unified utility to delete old sheets with same prefix but different timestamp.

    This function provides consistent logging and error handling for sheet cleanup operations.

    Args:
        service: Google Sheets API service
        spreadsheet_id: ID of the spreadsheet
        new_sheet_name: The newly created sheet name (with timestamp)
                       Example: "team - PR Report - Combined - 2026-01-18 10:43"
        reason: Human-readable reason for cleanup (for logging)

    Returns:
        List of deleted sheet names

    Example:
        If new_sheet_name is "team - PR Report - Combined - 2026-01-18 10:43"
        Will delete "team - PR Report - Combined - 2026-01-07 10:43" etc.
    """
    import re

    print(f"   🧹 Sheet cleanup started ({reason})")
    print(f"      New sheet: '{new_sheet_name}'")

    # Extract prefix by removing timestamp pattern (YYYY-MM-DD HH:MM at end)
    # Pattern: " - YYYY-MM-DD HH:MM" at the end
    timestamp_pattern = r" - \d{4}-\d{2}-\d{2} \d{2}:\d{2}$"
    prefix = re.sub(timestamp_pattern, "", new_sheet_name)

    if prefix == new_sheet_name:
        # No timestamp found in new sheet name, nothing to delete
        print(f"      ℹ️  Sheet name has no timestamp pattern, skipping cleanup")
        print(f"      Expected format: 'Name - YYYY-MM-DD HH:MM'")
        return []

    print(f"      Extracted prefix: '{prefix}'")
    print(f"      🔍 Scanning spreadsheet for matching sheets...")

    # Get all sheets
    try:
        spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        sheets = spreadsheet.get("sheets", [])
        print(f"      Found {len(sheets)} total sheet(s) in spreadsheet")
    except HttpError as e:
        print(f"      ⚠️  Failed to get sheets for cleanup: {e}")
        return []

    # Find sheets with same prefix but different timestamp
    sheets_to_delete = []
    all_matching_sheets = []

    for sheet in sheets:
        sheet_title = sheet["properties"]["title"]
        sheet_id = sheet["properties"]["sheetId"]

        # Track all sheets with same prefix for debugging
        if sheet_title.startswith(prefix):
            all_matching_sheets.append(sheet_title)

        # Check if this sheet has the same prefix
        if sheet_title.startswith(prefix + " - ") and sheet_title != new_sheet_name:
            # Verify it matches the pattern (has timestamp)
            if re.search(timestamp_pattern, sheet_title):
                sheets_to_delete.append({"title": sheet_title, "id": sheet_id})
                print(f"      ➜ Will delete: '{sheet_title}'")

    # Debug: show all sheets with matching prefix
    if all_matching_sheets:
        print(f"      All sheets with prefix '{prefix}': {len(all_matching_sheets)}")
        for sheet_title in all_matching_sheets:
            if sheet_title == new_sheet_name:
                print(f"         • '{sheet_title}' (current - keep)")
            elif sheet_title in [s["title"] for s in sheets_to_delete]:
                print(f"         • '{sheet_title}' (old - delete)")
            else:
                print(f"         • '{sheet_title}' (other - keep)")

    if not sheets_to_delete:
        print(f"      ✓ No old sheets to delete")
        if len(all_matching_sheets) == 1:
            print(f"      This is the first upload with this prefix")
        return []

    print(f"      🗑️  Deleting {len(sheets_to_delete)} old sheet(s)...")

    # Delete old sheets
    deleted_sheets = []
    requests = []
    for sheet in sheets_to_delete:
        requests.append({"deleteSheet": {"sheetId": sheet["id"]}})
        deleted_sheets.append(sheet["title"])

    try:
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id, body={"requests": requests}
        ).execute()

        print(f"      ✅ Successfully deleted {len(deleted_sheets)} sheet(s):")
        for sheet_name in deleted_sheets:
            print(f"         🗑️  {sheet_name}")

        return deleted_sheets
    except HttpError as e:
        print(f"      ⚠️  Failed to delete old sheets: {e}")
        print(f"      Attempted to delete: {deleted_sheets}")
        return []


def create_new_sheet_tab(service, spreadsheet_id, sheet_name):
    """
    Create a new sheet tab in the spreadsheet.

    Args:
        service: Google Sheets API service
        spreadsheet_id: ID of the spreadsheet
        sheet_name: Name for the new sheet tab

    Returns:
        Sheet ID of the newly created tab
    """
    request_body = {"requests": [{"addSheet": {"properties": {"title": sheet_name}}}]}

    response = (
        service.spreadsheets()
        .batchUpdate(spreadsheetId=spreadsheet_id, body=request_body)
        .execute()
    )

    # Get the newly created sheet ID
    sheet_id = response["replies"][0]["addSheet"]["properties"]["sheetId"]
    return sheet_id


def upload_data_to_sheet(
    service, spreadsheet_id, data, sheet_name="Sheet1", create_new_tab=True, replace_existing=False
):
    """
    Upload data to a Google Sheet.

    Args:
        service: Google Sheets API service
        spreadsheet_id: ID of the spreadsheet
        data: List of lists (rows)
        sheet_name: Base name of the sheet tab
        create_new_tab: If True, always create a new tab with timestamp
        replace_existing: If True, delete old sheets with same name but different timestamp

    Returns:
        tuple: (final_sheet_name, sheet_id)
    """
    # Get existing sheets
    existing_sheets = get_existing_sheets(service, spreadsheet_id)

    # Determine final sheet name
    if create_new_tab or sheet_name in existing_sheets:
        # Add timestamp to create unique name
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        final_sheet_name = f"{sheet_name} - {timestamp}"

        # If it's the first sheet and it's named "Sheet1", rename it
        if len(existing_sheets) == 1 and existing_sheets[0] == "Sheet1":
            try:
                service.spreadsheets().batchUpdate(
                    spreadsheetId=spreadsheet_id,
                    body={
                        "requests": [
                            {
                                "updateSheetProperties": {
                                    "properties": {"sheetId": 0, "title": final_sheet_name},
                                    "fields": "title",
                                }
                            }
                        ]
                    },
                ).execute()
                sheet_id = 0
                print(f"✓ Renamed default sheet to '{final_sheet_name}'")
            except HttpError:
                # If rename fails, create new tab
                sheet_id = create_new_sheet_tab(service, spreadsheet_id, final_sheet_name)
                print(f"✓ Created new sheet tab '{final_sheet_name}'")
        else:
            # Create new tab
            sheet_id = create_new_sheet_tab(service, spreadsheet_id, final_sheet_name)
            print(f"✓ Created new sheet tab '{final_sheet_name}'")
    else:
        # Use the provided name (new spreadsheet case)
        final_sheet_name = sheet_name
        sheet_id = 0

    # Upload data
    range_name = f"'{final_sheet_name}'!A1"
    body = {"values": data}

    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id, range=range_name, valueInputOption="RAW", body=body
    ).execute()

    print(f"✓ Uploaded {len(data)} rows to sheet '{final_sheet_name}'")

    # Delete old sheets with same prefix if replace_existing is True
    if replace_existing and create_new_tab:
        cleanup_old_sheets(
            service=service,
            spreadsheet_id=spreadsheet_id,
            new_sheet_name=final_sheet_name,
            reason="replace_existing=True",
        )

    return final_sheet_name, sheet_id


def format_sheet(service, spreadsheet_id, sheet_id=0):
    """
    Apply formatting to the sheet (header bold, freeze first row, etc).

    Args:
        service: Google Sheets API service
        spreadsheet_id: ID of the spreadsheet
        sheet_id: ID of the sheet tab (default 0)
    """
    requests = [
        # Freeze first row
        {
            "updateSheetProperties": {
                "properties": {"sheetId": sheet_id, "gridProperties": {"frozenRowCount": 1}},
                "fields": "gridProperties.frozenRowCount",
            }
        },
        # Bold header row
        {
            "repeatCell": {
                "range": {"sheetId": sheet_id, "startRowIndex": 0, "endRowIndex": 1},
                "cell": {"userEnteredFormat": {"textFormat": {"bold": True}}},
                "fields": "userEnteredFormat.textFormat.bold",
            }
        },
        # Auto-resize columns
        {
            "autoResizeDimensions": {
                "dimensions": {
                    "sheetId": sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": 0,
                    "endIndex": 10,
                }
            }
        },
    ]

    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id, body={"requests": requests}
    ).execute()

    print("✓ Applied formatting (frozen header, bold text, auto-resize)")


def get_service_account_email(credentials_file=None):
    """
    Get the service account email from credentials file.

    Args:
        credentials_file: Path to credentials JSON file

    Returns:
        Service account email address or None if not a service account
    """
    import json

    if not credentials_file:
        credentials_file = os.getenv("GOOGLE_CREDENTIALS_FILE")

    if not credentials_file or not os.path.exists(credentials_file):
        return None

    try:
        with open(credentials_file, "r") as f:
            creds_data = json.load(f)
            return creds_data.get("client_email")
    except Exception:
        return None


def get_sheets_service(credentials_file=None, timeout=60):
    """
    Get Google Sheets API service (convenience wrapper).

    Args:
        credentials_file: Path to credentials file (optional, uses env var if not provided)
        timeout: Timeout in seconds for API requests (default: 60)

    Returns:
        Google Sheets API service object
    """
    credentials = get_credentials(credentials_file)
    return build_service(credentials, timeout)


def build_service(credentials, timeout=60):
    """
    Build Google Sheets API service with timeout configuration.

    Args:
        credentials: Google API credentials
        timeout: Timeout in seconds for API requests (default: 60)

    Returns:
        Google Sheets API service object
    """
    import httplib2
    from google_auth_httplib2 import AuthorizedHttp

    # Create HTTP client with timeout
    # httplib2 automatically uses HTTP_PROXY/HTTPS_PROXY environment variables
    http = httplib2.Http(timeout=timeout)

    # Create authorized HTTP client with credentials and proxy support
    authorized_http = AuthorizedHttp(credentials, http=http)

    # Build the service with the authorized HTTP client
    # This ensures both proxy settings and credentials are used correctly
    service = build("sheets", "v4", http=authorized_http)

    return service
