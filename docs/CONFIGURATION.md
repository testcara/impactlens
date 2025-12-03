# Configuration Guide

This guide explains how to configure AI Impact Analysis for your team(s) and customize report generation.

## Table of Contents

- [Quick Start (Single Team)](#quick-start-single-team)
- [Configuration Options](#configuration-options)
- [Advanced Configuration](#advanced-configuration)
  - [Custom Config Files](#custom-config-files)
  - [Multi-Team Setup (Enterprise)](#multi-team-setup-enterprise)
  - [Google Sheets Integration](#google-sheets-integration)
- [Environment Variables](#environment-variables)
- [Best Practices & Security](#best-practices--security)
- [Troubleshooting](#troubleshooting)

## Quick Start (Single Team)

**Default Setup:**

By default, the tool uses:
- Config files: `config/jira_report_config.yaml`, `config/pr_report_config.yaml`
- Output directories: `reports/jira/`, `reports/github/`
- Environment: `.env` file

**Steps:**

1. Copy config templates:
   ```bash
   cp config/jira_report_config.yaml.example config/jira_report_config.yaml
   cp config/pr_report_config.yaml.example config/pr_report_config.yaml
   ```

2. Edit config files with your team's information (phases, team members)

3. Set environment variables (see [Environment Variables](#environment-variables))

4. Run analysis:
   ```bash
   ai-impact-analysis full
   ```

That's it! Reports will be generated in `reports/jira/` and `reports/github/`.

## Configuration Options

Both `config/jira_report_config.yaml` and `config/pr_report_config.yaml` support these options:

### 1. Phases (Required)

Define analysis periods for comparison (e.g., before/after AI adoption):

```yaml
phases:
  - name: "Before AI"
    start: "2024-01-01"
    end: "2024-06-30"
  - name: "With AI Tools"
    start: "2024-07-01"
    end: "2024-12-31"
```

**Notes:**
- Add as many phases as needed
- Use descriptive names (e.g., "No AI Period", "Cursor Only", "Claude + Cursor")
- Dates must be in YYYY-MM-DD format

### 2. Team Members (Optional)

For individual reports when using `--all-members` mode:

**Jira config:**
```yaml
team_members:
  - member: alice
    email: alice@company.com
    leave_days: 10      # or [10, 5] per phase
    capacity: 1.0       # 1.0 = full time, or [1.0, 0.5] per phase
  - member: bob
    email: bob@company.com
    leave_days: [5, 8]  # Different per phase
    capacity: [1.0, 0.0] # Left team in phase 2
```

**PR config:**
```yaml
team_members:
  - name: alice-github
  - name: bob-github
```

**Leave Days & Capacity Metrics:**

- **Leave Days**: Days the member was on leave during the phase
  - Can be single number (applies to all phases): `leave_days: 0`
  - Or list (one per phase): `leave_days: [26, 20, 11.5]`

- **Capacity**: Work capacity (0.0 to 1.0, where 1.0 = full time)
  - `1.0` = Full time (100%)
  - `0.8` = 80% time (e.g., 4 days/week)
  - `0.5` = Half time
  - `0.0` = Not on team (member left)
  - Can be single number or list per phase

Reports include **four Daily Throughput metrics** for comprehensive analysis:
1. Daily Throughput (skip leave days) = Total Issues / (Period - Leave Days)
2. Daily Throughput (based on capacity) = Total Issues / (Period × Capacity)
3. Daily Throughput (leave days + capacity) = Total Issues / ((Period - Leave Days) × Capacity)
4. Daily Throughput = Total Issues / Period (baseline)

### 3. Default Assignee/Author (Optional)

Control default report scope:

**Jira config:**
```yaml
default_assignee: ""  # "" = team reports (default)
                     # "email@company.com" = individual reports
```

**PR config:**
```yaml
default_author: ""    # "" = team reports (default)
                     # "username" = individual reports
```

Command line arguments override this setting.

### 4. Output Directory (Optional, for multi-team)

Customize where reports are saved:

```yaml
# Jira config
output_dir: "reports/jira"              # Default
output_dir: "reports/team-a/jira"       # Team-specific

# PR config
output_dir: "reports/github"            # Default
output_dir: "reports/team-a/github"     # Team-specific
```

If not specified, uses default directories.

### 5. AI Detection in Commits (PR reports)

The tool detects AI assistance from Git commit trailers:

```bash
# Claude assistance
git commit -m "Fix authentication bug

Assisted-by: Claude <noreply@anthropic.com>"

# Cursor assistance
git commit -m "Implement new feature

Assisted-by: Cursor"
```

Configure authorized emails in `AI_authorized_emails.txt` for AI analysis features.

## Advanced Configuration

### Custom Config Files

Create custom YAML files to override default settings. Only include values you want to change:

**Example: my-config.yaml**
```yaml
# Override only phases (keep default team members)
phases:
  - name: "Q1 2024"
    start: "2024-01-01"
    end: "2024-03-31"
  - name: "Q2 2024"
    start: "2024-04-01"
    end: "2024-06-30"
```

**Usage:**

All commands support `--config` parameter:

```bash
# Full workflow
ai-impact-analysis jira full --config my-config.yaml
ai-impact-analysis pr full --config my-config.yaml

# Individual commands
ai-impact-analysis jira team --config my-config.yaml
ai-impact-analysis jira member alice@company.com --config my-config.yaml
ai-impact-analysis jira members --config my-config.yaml
ai-impact-analysis jira all --config my-config.yaml
ai-impact-analysis jira combine --config my-config.yaml

ai-impact-analysis pr team --config my-config.yaml
ai-impact-analysis pr member alice --config my-config.yaml
ai-impact-analysis pr members --config my-config.yaml
ai-impact-analysis pr all --config my-config.yaml
ai-impact-analysis pr combine --config my-config.yaml
```

**How merging works:**
- Values in custom config override defaults from `config/jira_report_config.yaml` or `config/pr_report_config.yaml`
- Missing values in custom config are taken from default config

### Multi-Team Setup (Enterprise)

For organizations managing multiple teams, isolate configs and reports using separate directories.

**Naming Flexibility:**

Throughout this guide we use `team-a`, `team-b` as examples. You can use **any naming scheme**:
- By team: `frontend`, `backend`, `mobile`, `platform`
- By product: `product-x`, `product-y`
- By location: `us-team`, `eu-team`
- By individual: `alice`, `bob`

The tool is **completely flexible** - the examples use `team-a` for clarity.

#### Directory Structure

```
ai-analysis/
├── config/
│   ├── test/                     # CI integration test configs (internal use)
│   │   ├── jira_report_config.yaml
│   │   └── pr_report_config.yaml
│   ├── team-a/
│   │   ├── jira_report_config.yaml
│   │   └── pr_report_config.yaml
│   ├── team-b/
│   │   ├── jira_report_config.yaml
│   │   └── pr_report_config.yaml
│   └── team-c/
│       ├── jira_report_config.yaml
│       └── pr_report_config.yaml
├── reports/
│   ├── test/                     # CI test reports (auto-generated)
│   │   ├── jira/
│   │   └── github/
│   ├── team-a/
│   │   ├── jira/
│   │   └── github/
│   ├── team-b/
│   │   ├── jira/
│   │   └── github/
│   └── team-c/
│       ├── jira/
│       └── github/
├── .env.team-a
├── .env.team-b
├── .env.team-c
└── docker-compose.yml
```

#### Environment Files

Create separate environment files for each team:

**.env.team-a:**
```bash
# Jira configuration
JIRA_URL=https://issues.redhat.com
JIRA_API_TOKEN=team_a_token_here
JIRA_PROJECT_KEY=TEAM_A_PROJECT

# GitHub configuration
GITHUB_TOKEN=ghp_team_a_token
GITHUB_REPO_OWNER=org-name
GITHUB_REPO_NAME=team-a-repo

# Google Sheets (optional)
GOOGLE_CREDENTIALS_FILE=/path/to/team-a-credentials.json
GOOGLE_SPREADSHEET_ID=team_a_sheet_id

# AI Analysis (optional)
ANTHROPIC_API_KEY=sk-ant-team-a-key
```

**.env.team-b:**
```bash
# Similar structure with Team B specific values
JIRA_URL=https://issues.redhat.com
JIRA_API_TOKEN=team_b_token_here
JIRA_PROJECT_KEY=TEAM_B_PROJECT
# ... etc
```

#### Configuration Files

**config/team-a/jira_report_config.yaml:**
```yaml
# Custom output directory for team isolation
output_dir: "reports/team-a/jira"

phases:
  - name: "Before AI"
    start: "2024-01-01"
    end: "2024-06-30"
  - name: "With AI Tools"
    start: "2024-07-01"
    end: "2024-12-31"

default_assignee: ""

team_members:
  - member: alice
    email: alice@company.com
    leave_days: 10
    capacity: 1.0
  - member: bob
    email: bob@company.com
    leave_days: 5
    capacity: 0.8
```

**config/team-a/pr_report_config.yaml:**
```yaml
# Custom output directory for team isolation
output_dir: "reports/team-a/github"

phases:
  - name: "Before AI"
    start: "2024-01-01"
    end: "2024-06-30"
  - name: "With AI Tools"
    start: "2024-07-01"
    end: "2024-12-31"

default_author: ""

team_members:
  - name: alice-github
  - name: bob-github
```

#### Usage

**CLI Usage:**

```bash
# Recommended: Directory config (auto-finds both jira & pr configs)
source .env.team-a
ai-impact-analysis full --config config/team-a

# Alternative: Specific files
source .env.team-a
ai-impact-analysis jira full --config config/team-a/jira_report_config.yaml
ai-impact-analysis pr full --config config/team-a/pr_report_config.yaml

# All other commands also support --config (see "Custom Config Files" section for full list)
```

**Docker Usage:**

**Important:** The `--env-file` flag must be placed **before** `run`.

```bash
# Recommended: Directory config
docker-compose --env-file .env.team-a run ai-impact-analysis \
  full --config /app/config/team-a

# Alternative: Specific files
docker-compose --env-file .env.team-a run ai-impact-analysis \
  jira full --config /app/config/team-a/jira_report_config.yaml

docker-compose --env-file .env.team-a run ai-impact-analysis \
  pr full --config /app/config/team-a/pr_report_config.yaml

# All other commands also support --config (see "Custom Config Files" section for full list)
```

**Config Parameter Behavior:**
- **Directory** (e.g., `config/team-a`): Auto-finds `jira_report_config.yaml` and `pr_report_config.yaml`
- **Specific file** (e.g., `config/team-a/jira_report_config.yaml`): Uses that specific file

#### Output Structure

Each team's reports are isolated:

```
reports/
├── team-a/
│   ├── jira/
│   │   ├── jira_report_general_*.txt
│   │   ├── comparison_report_general_*.tsv
│   │   └── combined_jira_report_*.tsv
│   └── github/
│       ├── pr_report_general_*.txt
│       ├── pr_comparison_general_*.tsv
│       └── combined_pr_report_*.tsv
└── team-b/
    ├── jira/
    └── github/
```

#### Automation Scripts

Create wrapper scripts for convenience:

**scripts/run-team-analysis.sh:**
```bash
#!/bin/bash
# Usage: ./scripts/run-team-analysis.sh team-a full

TEAM=$1
MODE=$2  # full, jira, or pr

if [ -z "$TEAM" ] || [ -z "$MODE" ]; then
    echo "Usage: $0 <team-name> <full|jira|pr>"
    exit 1
fi

ENV_FILE=".env.$TEAM"
CONFIG_DIR="config/$TEAM"

if [ ! -f "$ENV_FILE" ]; then
    echo "Error: Environment file $ENV_FILE not found"
    exit 1
fi

if [ ! -d "$CONFIG_DIR" ]; then
    echo "Error: Config directory $CONFIG_DIR not found"
    exit 1
fi

echo "Running $MODE analysis for $TEAM..."
docker-compose --env-file "$ENV_FILE" run ai-impact-analysis \
  $MODE --config "/app/$CONFIG_DIR"
```

**Usage:**
```bash
chmod +x scripts/run-team-analysis.sh

# Run full workflow for Team A
./scripts/run-team-analysis.sh team-a full

# Run only Jira analysis for Team B
./scripts/run-team-analysis.sh team-b jira
```

#### Migration from Single Team

If migrating from single-team setup:

1. **Backup existing reports:**
   ```bash
   cp -r reports reports.backup
   ```

2. **Create team-specific structure:**
   ```bash
   mkdir -p config/team-default
   cp config/*.yaml config/team-default/
   ```

3. **Update config with output_dir:**
   ```yaml
   output_dir: "reports/team-default/jira"
   ```

4. **Test new structure:**
   ```bash
   docker-compose run ai-impact-analysis verify
   ```

### Google Sheets Integration

Reports can be **automatically uploaded** to Google Sheets if configured.

#### Setup (one-time)

```bash
# 1. Install Google Sheets dependencies
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client

# 2. Create Service Account at https://console.cloud.google.com
#    - Create project and enable Google Sheets API
#    - Create Service Account credentials
#    - Download JSON key file
#    - Note the Service Account email (client_email in JSON)

# 3. Create Google Spreadsheet
#    - Go to https://sheets.google.com and create new spreadsheet
#    - Name it like: "AI Analysis - Team A"
#    - Click "Share" and add Service Account email with Editor permission
#    - Copy Spreadsheet ID from URL: https://docs.google.com/spreadsheets/d/[SPREADSHEET_ID]/edit

# 4. Configure environment variables
export GOOGLE_CREDENTIALS_FILE="/path/to/service-account-key.json"
export GOOGLE_SPREADSHEET_ID="1ABCdefGHI..."
```

#### Usage

```bash
# Automatic upload (if environment variables configured)
ai-impact-analysis jira full    # Generates & auto-uploads Jira reports
ai-impact-analysis pr full      # Generates & auto-uploads PR reports

# Skip upload with --no-upload flag
ai-impact-analysis jira full --no-upload
ai-impact-analysis pr full --no-upload
```

#### Features

- Each upload creates a new tab with timestamp (e.g., "Team A Report - 2024-12-01 14:30")
- All previous tabs are preserved for historical tracking
- You can use the same spreadsheet for both Jira and GitHub reports (different tabs)
- If auto-upload not configured, scripts show manual upload instructions

## Environment Variables

### Required for Jira Analysis

```bash
export JIRA_URL="https://issues.redhat.com"
export JIRA_API_TOKEN="your_api_token_here"
export JIRA_PROJECT_KEY="Your Project Name"
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

**For CLI (single team):**

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

**For multi-team:**

Use separate `.env.team-name` files and load with:
- **CLI**: `source .env.team-a` before running commands
- **Docker**: `docker-compose --env-file .env.team-a run ...`

## Best Practices & Security

### Security

- ✅ **Keep `.env*` files in `.gitignore`** - Never commit credentials
- ✅ **Use separate service accounts per team** - Better access control
- ✅ **Rotate tokens regularly** - Minimize security risks
- ✅ **Use minimal permissions** - Read-only access where possible

### Organization

- ✅ **Use consistent naming** - `.env.team-name`, `config/team-name/`
- ✅ **Document team configurations** - Maintain a team registry
- ✅ **Create template configs** - Easier to onboard new teams
- ✅ **Centralize common phase definitions** - If teams share analysis periods

### Maintenance

- ✅ **Regular backups of reports** - Preserve historical data
- ✅ **Version control for configs** - Track configuration changes (exclude `.env` files)
- ✅ **Test new configurations** - Use `verify` command before full runs

## Troubleshooting

### Common Issues

**1. No config files found:**
```bash
# Check if templates exist
ls -la config/*.example

# Copy templates
cp config/jira_report_config.yaml.example config/jira_report_config.yaml
cp config/pr_report_config.yaml.example config/pr_report_config.yaml
```

**2. Environment variables not loaded (Docker):**
```bash
# Verify which env is loaded
docker-compose --env-file .env.team-a config | grep JIRA_PROJECT_KEY

# Make sure --env-file is BEFORE run
docker-compose --env-file .env.team-a run ai-impact-analysis verify
```

**3. Reports in wrong directory:**
- Check `output_dir` in config file
- Ensure path uses forward slashes (`reports/team-a/jira` not `reports\team-a\jira`)
- Verify directory is writable

**4. Config not found (multi-team):**
```bash
# CLI - Check if config exists
ls -la config/team-a/

# Docker - Check inside container
docker-compose run ai-impact-analysis ls -la /app/config/team-a/
```

**5. Google Sheets upload fails:**
- Verify service account email has Editor permission on spreadsheet
- Check credentials file path is correct
- Ensure Google Sheets API is enabled in Cloud Console

**6. No team members found:**
- Ensure config file exists (not just `.example` template)
- Check YAML syntax is correct (proper indentation)
- Verify team_members section is not empty

For more help, check the [main README](../README.md) or open an issue on GitHub.
