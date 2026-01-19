#!/bin/bash
# Test analysis prompt generation for combined reports
# Usage: ./test-prompt-generation.sh <reports_base_dir>
# Example: ./test-prompt-generation.sh "reports/test-ci-team*"

set -e

REPORTS_PATTERN="${1:-reports/test-ci-team*}"

echo "=========================================="
echo "Testing Analysis Prompt Generation"
echo "=========================================="
echo ""

# Enable recursive globbing
shopt -s globstar nullglob

PROMPT_COUNT=0
FAILED_COUNT=0

# Test prompt generation for both Jira and PR combined reports
for pattern in "combined_jira_report" "combined_pr_report"; do
  for report in ${REPORTS_PATTERN}/**/${pattern}_*.tsv; do
    if [ -f "$report" ]; then
      echo "Testing prompt generation for: $report"

      # Extract directory and determine output
      output_dir="$(dirname "$report")/prompts-test"
      mkdir -p "$output_dir"

      if python -m impactlens.scripts.generate_analysis_prompt \
        --reports-dir "$report" \
        --prompt-only \
        --output-dir "$output_dir" 2>&1; then
        echo "  ✓ Prompt generated successfully"
        PROMPT_COUNT=$((PROMPT_COUNT + 1))
      else
        echo "  ✗ Failed to generate prompt"
        FAILED_COUNT=$((FAILED_COUNT + 1))
      fi
      echo ""
    fi
  done
done

echo "=========================================="
echo "Prompt Generation Test Summary"
echo "=========================================="
echo "  Prompts generated: $PROMPT_COUNT"
echo "  Failed: $FAILED_COUNT"

if [ $PROMPT_COUNT -eq 0 ]; then
  echo ""
  echo "⚠️  No combined reports found for prompt generation test"
  echo "   This is expected if report generation was skipped"
elif [ $FAILED_COUNT -gt 0 ]; then
  echo ""
  echo "✗ Some prompt generations failed"
  exit 1
else
  echo ""
  echo "✓ All prompt generation tests passed"
fi
