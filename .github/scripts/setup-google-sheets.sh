#!/bin/bash
# Setup Google Sheets credentials for CI
# Usage: ./setup-google-sheets.sh

set -e

if [ -n "$GOOGLE_CREDENTIALS_BASE64" ]; then
    echo "Setting up Google Sheets credentials..."
    echo "$GOOGLE_CREDENTIALS_BASE64" | base64 -d > /tmp/google_credentials.json
    echo "GOOGLE_CREDENTIALS_FILE=/tmp/google_credentials.json" >> "$GITHUB_ENV"
    echo "✓ Google Sheets credentials configured"
else
    echo "⚠️  GOOGLE_CREDENTIALS_BASE64 not set, uploads will be skipped"
fi
