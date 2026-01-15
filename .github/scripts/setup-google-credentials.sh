#!/bin/bash
# Setup Google Sheets credentials for CI
# Usage: ./setup-google-credentials.sh
#
# Required environment variables:
#   GOOGLE_CREDENTIALS_BASE64 - Base64 encoded service account JSON
#
set -e

if [ -z "$GOOGLE_CREDENTIALS_BASE64" ]; then
    echo "   To enable uploads, add GOOGLE_CREDENTIALS_BASE64 secret in repository settings"
    exit 0
fi

# Decode and save credentials
echo "Setting up Google credentials..."
echo "$GOOGLE_CREDENTIALS_BASE64" | base64 -d > /tmp/google-credentials.json

# Verify the file was created and is valid JSON
if [ ! -f /tmp/google-credentials.json ]; then
    echo "❌ Failed to create credentials file"
    exit 1
fi

if ! python3 -m json.tool /tmp/google-credentials.json > /dev/null 2>&1; then
    echo "❌ Credentials file is not valid JSON"
    rm -f /tmp/google-credentials.json
    exit 1
fi

# Set environment variable for subsequent steps
echo "GOOGLE_CREDENTIALS_FILE=/tmp/google-credentials.json" >> "$GITHUB_ENV"
echo "✓ Google credentials configured successfully"

# Export for the check script
export GOOGLE_CREDENTIALS_FILE=/tmp/google-credentials.json
