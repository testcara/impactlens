#!/bin/bash
# Check if code or specific test configs changed
# Usage: ./check-code-changed.sh <config_pattern>
# Example: ./check-code-changed.sh "test-integration-ci"
# Output: Sets GITHUB_OUTPUT with code_changed=true/false

set -e

CONFIG_PATTERN="${1:-test-(integration|aggregation)-ci}"

if [ "$GITHUB_EVENT_NAME" = "pull_request" ]; then
  FILES=$(git diff --name-only "$GITHUB_BASE_SHA" "$GITHUB_SHA")

  # Check for test config changes
  TEST_CONFIG_FILES=$(echo "$FILES" | grep -E "^config/${CONFIG_PATTERN}/.*\.(yaml|yml)$" || true)

  # Check for code/non-doc changes
  CODE_CHANGED=$(echo "$FILES" | grep -qvE '^(README\.md|docs/.*|config/.*\.example|LICENSE|\.gitignore|config/[^/]+/.*\.(yaml|yml)$)' && echo "true" || echo "false")

  if [ -n "$TEST_CONFIG_FILES" ] || [ "$CODE_CHANGED" = "true" ]; then
    echo "code_changed=true" >> "$GITHUB_OUTPUT"
    if [ -n "$TEST_CONFIG_FILES" ]; then
      echo "✅ Test config files changed - running tests"
    fi
  else
    echo "code_changed=false" >> "$GITHUB_OUTPUT"
    echo "⏭️ Only docs/user configs changed - skipping tests"
  fi
else
  echo "code_changed=true" >> "$GITHUB_OUTPUT"
fi
