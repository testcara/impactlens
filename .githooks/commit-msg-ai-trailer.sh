#!/bin/bash
# Git commit-msg hook: automatically adds "Assisted-by" trailers for AI tool
# usage (Claude/Cursor) based on running processes and commit message content
# for authorized users.

set -euo pipefail

COMMIT_MSG_FILE="$1"

# If the commit message is fixup! or squash! or Merge, exit without changing it.
grep -qE '^(fixup!|squash!|Merge)' "$COMMIT_MSG_FILE" && exit 0

# Get repository root
REPO_ROOT=$(git rev-parse --show-toplevel)

# Load authorized emails from AI_authorized_emails.txt
AUTHORIZED_EMAILS=()
EMAILS_FILE="$REPO_ROOT/AI_authorized_emails.txt"

if [ -f "$EMAILS_FILE" ]; then
  while IFS= read -r line; do
    # Skip empty lines and comments
    [[ -z "$line" || "$line" =~ ^# ]] && continue
    AUTHORIZED_EMAILS+=("$line")
  done < "$EMAILS_FILE"
fi

# Get current user's email
CURRENT_EMAIL=$(git config user.email)

# Check if the email is set
if [ -z "$CURRENT_EMAIL" ]; then
  echo "Warning: Current email is not set, skipping AI trailer"
  exit 0
fi

# Check if the email is in the authorized list
is_authorized=0
for email in "${AUTHORIZED_EMAILS[@]}"; do
  if [ "$CURRENT_EMAIL" = "$email" ]; then
    is_authorized=1
    break
  fi
done

if [ "$is_authorized" -eq 0 ]; then
  # User not authorized, exit silently
  exit 0
fi

# Function to check if AI process is running in this repo
check_ai_process_in_repo() {
  local ai_pattern="$1"
  for pid in $(pgrep -f "$ai_pattern" 2>/dev/null || true); do
    # Only proceed if /proc exists (Linux)
    if [ -d "/proc/$pid" ]; then
      cwd=$(readlink "/proc/$pid/cwd" 2>/dev/null || echo "")
      if [[ "$cwd" == "$REPO_ROOT"* ]]; then
        echo "true"
        return
      fi
    fi
  done
  echo "false"
}

claude_active=$(check_ai_process_in_repo "claude")
cursor_active=$(check_ai_process_in_repo "cursor")

# Fallback: check commit message content for AI markers
COMMIT_MSG_CONTENT=$(cat "$COMMIT_MSG_FILE" || echo "")

if [ "$claude_active" != "true" ]; then
  if echo "$COMMIT_MSG_CONTENT" | grep -qiE "(claude|anthropic|Generated with.*Claude Code|Co-Authored-By: Claude)"; then
    claude_active="true"
  fi
fi

if [ "$cursor_active" != "true" ]; then
  if echo "$COMMIT_MSG_CONTENT" | grep -qiE "(cursor|Co-Authored-By: cursor)"; then
    cursor_active="true"
  fi
fi

# Determine which trailer to add
TRAILER=""

if [ "$claude_active" = "true" ] && [ "$cursor_active" = "true" ]; then
  TRAILER="Assisted-by: Cursor, Claude"
elif [ "$claude_active" = "true" ]; then
  TRAILER="Assisted-by: Claude"
elif [ "$cursor_active" = "true" ]; then
  TRAILER="Assisted-by: Cursor"
fi

# Add trailer if it doesn't already exist
if [ -n "$TRAILER" ] && ! grep -qiE "^$TRAILER" "$COMMIT_MSG_FILE"; then
  git interpret-trailers --in-place --trailer "$TRAILER" "$COMMIT_MSG_FILE"
fi

exit 0
