# Configuration Guide

This guide explains how to configure AI Impact Analysis for your team and customize report generation.

## Table of Contents

- [Configuration Files](#configuration-files)
- [Jira Report Configuration](#jira-report-configuration)
- [GitHub PR Configuration](#github-pr-configuration)
- [Google Sheets Integration](#google-sheets-integration)
- [Custom Configuration](#custom-configuration)
- [Environment Variables](#environment-variables)

## Configuration Files

The tool uses YAML configuration files for report customization:

- `config/jira_report_config.yaml` - Jira analysis configuration (phases, assignees, team members)
- `config/pr_report_config.yaml` - GitHub PR analysis configuration (phases, authors, team members)
- `config/analysis_prompt_template.yaml` - AI analysis prompt customization (experimental feature)

## Jira Report Configuration

Edit `config/jira_report_config.yaml` to configure analysis periods, default assignee, and team members:

```yaml
# config/jira_report_config.yaml

# Define analysis phases (flexible: 1 to many)
phases:
  - name: "No AI Period"
    start: "2024-10-24"
    end: "2025-05-30"
  - name: "Cursor Period"
    start: "2025-06-02"
    end: "2025-07-31"
  - name: "Full AI Period"
    start: "2025-08-01"
    end: "2025-11-03"

# Default assignee (optional)
# - Set to "" for team overall reports (default)
# - Set to email for individual reports (e.g., "wlin@redhat.com")
# - Command line argument will override this value
default_assignee: ""

# Team members (optional, for --all-members mode)
team_members:
  - member: wlin
    email: wlin@redhat.com
    leave_days:
      - 26 # No AI Period
      - 20 # Cursor Period
      - 11.5 # Full AI Period
    capacity: 0.8
  - member: sbudhwar
    email: sbudhwar@redhat.com
    leave_days: 0
    capacity: 1.0
  - member: abhindas
    email: abhindas@redhat.com
    leave_days: 0
    capacity:
      - 1.0 # No AI Period (full time)
      - 1.0 # Cursor Period (full time)
      - 0.0 # Full AI Period (left team)
```

### Phase Configuration

- **Add as many phases** as needed for your analysis
- **Use descriptive names** (e.g., "No AI Period", "Cursor Only", "Claude + Cursor")
- **Dates must be** in YYYY-MM-DD format

### Team Members Configuration

- `member`: Jira username
- `email`: Email address for filtering
- `leave_days`: Leave days for each phase
  - Can be a single number (applies to all phases): `leave_days: 0`
  - Or a list (one value per phase): `leave_days: [26, 20, 11.5]`
- `capacity`: Work capacity (0.0 to 1.0, where 1.0 = full time)
  - Can be a single number (applies to all phases): `capacity: 0.8`
  - Or a list (one value per phase): `capacity: [1.0, 1.0, 0.0]`
  - Use 0.0 to indicate member left team in that phase

### Assignee Configuration

- Leave `default_assignee: ""` for team reports
- Set `default_assignee: "wlin@redhat.com"` to always generate reports for specific person
- Command line argument overrides config: `ai-impact-analysis jira member other@redhat.com`

### Understanding Leave Days and Capacity

These metrics help calculate more accurate throughput by accounting for time off and work capacity:

**Leave Days**: Days the team member was on leave during the phase

- Displayed in single reports and comparison reports
- Can be specified per phase (list) or as single value
- For team reports: sum of all members' leave days

**Capacity**: Work capacity as percentage of full-time (0.0 to 1.0)

- `1.0` = Full time (100%)
- `0.8` = 80% time (e.g., 4 days/week)
- `0.5` = Half time
- `0.0` = Not on team (member left)
- For team reports: sum of all members' capacity (total FTE)

**Data Span**: Always calculated as Phase end date - Phase start date + 1

```bash
# Example: Phase from 2024-01-01 to 2024-01-31
# Data Span = 31 days (includes both start and end dates)
```

### How Metrics Use Leave Days and Capacity

Reports include **four Daily Throughput metrics** to provide comprehensive analysis:

1. **Daily Throughput (skip leave days)** = Total Issues / (Analysis Period - Leave Days)

   - Accounts for vacation time

2. **Daily Throughput (based on capacity)** = Total Issues / (Analysis Period × Capacity)

   - Accounts for part-time work

3. **Daily Throughput (considering leave days + capacity)** = Total Issues / ((Analysis Period - Leave Days) × Capacity)

   - Most accurate: accounts for both vacation and capacity

4. **Daily Throughput** = Total Issues / Analysis Period
   - Baseline metric for comparison

## GitHub PR Configuration

Edit `config/pr_report_config.yaml` to configure analysis periods and team members:

```yaml
# config/pr_report_config.yaml

phases:
  - name: "No AI Period"
    start: "2024-10-24"
    end: "2025-05-30"
  - name: "Cursor Period"
    start: "2025-06-02"
    end: "2025-07-31"
  - name: "Full AI Period"
    start: "2025-08-01"
    end: "2025-11-03"

# Default author (optional)
# - Set to "" for team overall reports (default)
# - Set to GitHub username for individual reports (e.g., "wlin")
default_author: ""

# Team members (optional, for --all-members mode)
team_members:
  - name: testcara
  - name: wlin
  - name: sahil143
```

### AI Detection in Commits

The tool detects AI assistance from Git commit trailers. Add these to your commit messages:

```bash
# For Claude assistance
git commit -m "Fix authentication bug

Assisted-by: Claude <noreply@anthropic.com>"

# For Cursor assistance
git commit -m "Implement new feature

Assisted-by: Cursor"

# Both tools (multiple commits in PR)
# Some commits with Claude, some with Cursor
```

## Google Sheets Integration

Reports can be **automatically uploaded** to Google Sheets if configured.

### Setup (one-time)

```bash
# 1. Install Google Sheets dependencies
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client

# 2. Create Service Account at https://console.cloud.google.com
#    - Create project and enable Google Sheets API
#    - Create Service Account credentials
#    - Download JSON key file
#    - Note the Service Account email (client_email in JSON)

# 3. Create Google Spreadsheet (recommended)
#    - Go to https://sheets.google.com and create new spreadsheet
#    - Name it like: "AI Analysis - wlin"
#    - Click "Share" and add Service Account email with Editor permission
#    - Copy Spreadsheet ID from URL: https://docs.google.com/spreadsheets/d/[SPREADSHEET_ID]/edit

# 4. Configure environment variables for automatic upload
export GOOGLE_CREDENTIALS_FILE="/path/to/service-account-key.json"
export GOOGLE_SPREADSHEET_ID="1ABCdefGHI..."

# Add to ~/.bashrc for persistence
echo 'export GOOGLE_CREDENTIALS_FILE="/path/to/service-account-key.json"' >> ~/.bashrc
echo 'export GOOGLE_SPREADSHEET_ID="1ABCdefGHI..."' >> ~/.bashrc
```

### Usage

```bash
# Automatic upload (if environment variables configured)
ai-impact-analysis jira full    # Generates & auto-uploads Jira reports
ai-impact-analysis pr full      # Generates & auto-uploads PR reports

# Skip upload with --no-upload flag
ai-impact-analysis jira full --no-upload
ai-impact-analysis pr full --no-upload

# Manual upload of existing reports (advanced)
python3 -m ai_impact_analysis.scripts.upload_to_sheets --report reports/comparison_report_wlin_*.tsv
python3 -m ai_impact_analysis.scripts.upload_to_sheets --report reports/github/pr_comparison_wlin_*.tsv
```

### Features

- Each upload creates a new tab with timestamp (e.g., "wlin Report - 2025-10-24 14:30")
- All previous tabs are preserved for historical tracking
- You can use the same spreadsheet for both Jira and GitHub reports (different tabs)
- If auto-upload not configured, scripts show manual upload instructions

## Custom Configuration

You can create a custom YAML file to override default settings. Only include the values you want to change:

### Example Custom Config

```yaml
# my-config.yaml - Example custom config

# Override only phases (keep default team members)
phases:
  - name: "Q1 2024"
    start: "2024-01-01"
    end: "2024-03-31"
  - name: "Q2 2024"
    start: "2024-04-01"
    end: "2024-06-30"

# Or override only team members (keep default phases)
team_members:
  - member: alice
    email: alice@company.com
    leave_days: 5
    capacity: 1.0
  - member: bob
    email: bob@company.com
    leave_days: 0
    capacity: 0.5
```

### Using Custom Config

```bash
# Full report workflows with custom config
ai-impact-analysis jira full --config my-config.yaml
ai-impact-analysis pr full --config my-config.yaml

# Specific report types
ai-impact-analysis jira team --config my-config.yaml
ai-impact-analysis jira member alice@company.com --config my-config.yaml

# Advanced: For individual phase report (using script directly)
python3 -m ai_impact_analysis.scripts.get_jira_metrics --start 2024-01-01 --end 2024-03-31 --config my-config.yaml
```

### How Config Merging Works

- Values in custom config override defaults from `config/jira_report_config.yaml`
- Missing values in custom config are taken from default config
- This allows you to change only what you need without duplicating entire config

## Environment Variables

### Required for Jira Analysis

```bash
export JIRA_URL="https://issues.redhat.com"
export JIRA_API_TOKEN="your_api_token_here"
export JIRA_PROJECT_KEY="Konflux UI"
```

### Required for GitHub PR Analysis

```bash
export GITHUB_TOKEN="your_github_token"
export GITHUB_REPO_OWNER="your-org-or-username"
export GITHUB_REPO_NAME="your-repo-name"
```

### Optional - Google Sheets Integration

```bash
export GOOGLE_CREDENTIALS_FILE="/path/to/service-account-key.json"
export GOOGLE_SPREADSHEET_ID="1ABCdefGHI..."
```

### Optional - AI Analysis (Experimental)

```bash
# If using Anthropic API instead of Claude Code CLI
export ANTHROPIC_API_KEY="sk-ant-..."
```

### Making Environment Variables Persistent

Add to `~/.bashrc` or `~/.zshrc`:

```bash
# Jira
export JIRA_URL="https://issues.redhat.com"
export JIRA_API_TOKEN="your_token"
export JIRA_PROJECT_KEY="Your Project"

# GitHub
export GITHUB_TOKEN="your_token"
export GITHUB_REPO_OWNER="your-org"
export GITHUB_REPO_NAME="your-repo"

# Google Sheets (optional)
export GOOGLE_CREDENTIALS_FILE="/path/to/credentials.json"
export GOOGLE_SPREADSHEET_ID="your_sheet_id"
```

Then reload: `source ~/.bashrc`

### Authorized Emails for AI Detection

Before running AI analysis commands, update the authorized emails list:

Edit [`AI_authorized_emails.txt`](../AI_authorized_emails.txt) to include email addresses that should be analyzed for AI assistance.
