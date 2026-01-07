#!/bin/bash
# Determine upload arguments based on Google Sheets configuration
# Usage: UPLOAD_ARGS=$(./get-upload-args.sh)
# Output: "--no-upload" if not configured, empty string if configured

set -e

if [ -z "$GOOGLE_CREDENTIALS_FILE" ] || [ -z "$GOOGLE_SPREADSHEET_ID" ]; then
    echo "--no-upload"
else
    echo ""
fi
