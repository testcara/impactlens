#!/bin/bash
# 检测配置文件中是否需要访问内部 GitLab
# Usage: ./detect-internal-gitlab.sh <config_dir>

CONFIG_DIR="${1:-.}"
NEEDS_INTERNAL=false

echo "Checking for internal GitLab access in: $CONFIG_DIR"

# 检查所有相关的 pr_report_config.yaml
if [ -f "$CONFIG_DIR/aggregation_config.yaml" ]; then
  # Aggregation mode: 检查所有子项目
  echo "Aggregation mode detected"
  for project_dir in "$CONFIG_DIR"/*/; do
    if [ -f "$project_dir/pr_report_config.yaml" ]; then
      echo "Checking: $project_dir/pr_report_config.yaml"
      if grep -q "gitlab\.cee\.redhat\.com\|gitlab\.internal\|gitlab\.corp" "$project_dir/pr_report_config.yaml"; then
        echo "✓ Found internal GitLab URL in $project_dir/pr_report_config.yaml"
        NEEDS_INTERNAL=true
        break
      fi
    fi
  done
else
  # Single team mode
  if [ -f "$CONFIG_DIR/pr_report_config.yaml" ]; then
    echo "Checking: $CONFIG_DIR/pr_report_config.yaml"
    if grep -q "gitlab\.cee\.redhat\.com\|gitlab\.internal\|gitlab\.corp" "$CONFIG_DIR/pr_report_config.yaml"; then
      echo "✓ Found internal GitLab URL"
      NEEDS_INTERNAL=true
    fi
  fi
fi

if [ "$NEEDS_INTERNAL" = "true" ]; then
  echo "needs_internal_access=true"
  exit 0  # Needs self-hosted runner
else
  echo "needs_internal_access=false"
  exit 1  # Can use GitHub hosted runner
fi
