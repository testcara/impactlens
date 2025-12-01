# AI Impact Analysis

**A data-driven tool to quantify the impact of AI coding assistants on development efficiency through Jira and GitHub metrics.**

## Table of Contents

- [Overview](#overview)
- [Architecture & Project Structure](#architecture--project-structure)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Usage Examples](#usage-examples)
- [AI-Powered Analysis](#ai-powered-analysis-experimental)
- [Understanding Metrics](#understanding-metrics)
- [Documentation & Contributing](#documentation--contributing)
  - [For Users](#for-users) - Configuration & Metrics guides
  - [For Contributors](#for-contributors) - Contributing guide

## Overview

A Python tool that quantifies the impact of AI coding assistants through objective, data-driven metrics from Jira and GitHub.

**Business Value:**

- **Measure AI ROI**: Compare development efficiency before and after AI tool adoption
- **Data-Driven Decisions**: Use objective metrics (closure time, merge time, throughput) to evaluate AI effectiveness
- **Team & Individual Insights**: Understand AI impact at organization and contributor levels
- **Enterprise-Ready**: Multi-team support with isolated configs and reports for large organizations
- **Automated Reporting**: Generate comprehensive reports with one command
- **Shareable Results**: Auto-upload to Google Sheets for stakeholder visibility

**Use Cases:**

- Engineering leaders evaluating AI tool investments
- Teams measuring productivity improvements
- Researchers studying AI coding assistant effectiveness
- Organizations tracking developer efficiency over time

## Architecture & Project Structure

### System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLI Interface                            │
│                      (ai-impact-analysis)                        │
└──────────────┬──────────────────────────────┬───────────────────┘
               │                              │
       ┌───────▼────────┐            ┌────────▼──────────┐
       │  Jira Workflow │            │   PR Workflow     │
       └───────┬────────┘            └────────┬──────────┘
               │                              │
       ┌───────▼────────┐            ┌────────▼──────────┐
       │  Jira Client   │            │  GitHub Client    │
       │  (REST/GraphQL)│            │   (GraphQL)       │
       └───────┬────────┘            └────────┬──────────┘
               │                              │
               └──────────┬───────────────────┘
                          │
                 ┌────────▼──────────┐
                 │  Metrics           │
                 │  Calculators       │
                 └────────┬───────────┘
                          │
                 ┌────────▼──────────┐
                 │  Report            │
                 │  Generators        │
                 └────────┬───────────┘
                          │
          ┌───────────────┼───────────────┐
          │               │               │
  ┌───────▼────────┐ ┌───▼────┐ ┌────────▼──────────┐
  │ Google Sheets  │ │  TSV   │ │  Claude Analysis  │
  │    Upload      │ │ Files  │ │  (Optional)       │
  └────────────────┘ └────────┘ └───────────────────┘
```

**Key Components:**

- **CLI Interface**: Unified command-line interface (`cli.py`)
- **Clients**: API integrations (Jira REST/GraphQL, GitHub GraphQL, Google Sheets)
- **Core Logic**: Metrics calculators and report generators
- **Output**: TSV reports, Google Sheets upload, AI-powered insights

### Directory Structure

```
ai-impact-analysis/
├── ai_impact_analysis/           # Core library
│   ├── cli.py                    # CLI entry point
│   ├── clients/                  # API clients
│   │   ├── jira_client.py        # Jira REST API
│   │   ├── github_client_graphql.py  # GitHub GraphQL
│   │   └── sheets_client.py      # Google Sheets
│   ├── core/                     # Business logic
│   │   ├── jira_metrics_calculator.py
│   │   ├── pr_metrics_calculator.py
│   │   ├── jira_report_generator.py
│   │   ├── pr_report_generator.py
│   │   └── report_orchestrator.py
│   ├── models/                   # Data models & config
│   ├── scripts/                  # Script modules
│   │   ├── analyze_with_claude_code.py
│   │   ├── get_jira_metrics.py
│   │   ├── get_pr_metrics.py
│   │   ├── generate_*_report.py
│   │   └── verify_setup.py
│   └── utils/                    # Utilities
├── config/                       # Configuration files
│   ├── jira_report_config.yaml
│   ├── pr_report_config.yaml
│   └── analysis_prompt_template.yaml
├── docs/                         # Documentation
├── tests/                        # Test suite
├── reports/                      # Generated reports
│   ├── jira/                     # Jira reports
│   └── github/                   # PR reports
├── .env.example                  # Environment template
├── docker-compose.yml            # Docker setup
├── Dockerfile                    # Docker build config
├── pyproject.toml                # Project & CLI config
└── tox.ini                       # Test configuration
```

## Quick Start

### 1. Install

**Docker (Recommended):**

Precondition: `docker` and `docker-compose` (or `podman` and `podman-compose`) have been installed.

```bash
git clone https://github.com/testcara/ai_impact_analysis.git
cd ai_impact_analysis

# Optional: Pull pre-built image (auto-pulled on first run if not present)
docker-compose pull
```

> **Note:** The Docker image is automatically built from the `master` branch and hosted on [Quay.io](https://quay.io/repository/carawang/ai-impact-analysis). You don't need to build locally unless you're developing/testing code changes.

**CLI:**

```bash
git clone https://github.com/testcara/ai_impact_analysis.git
cd ai_impact_analysis
# Recommended:
# python3 -m venv venv && source venv/bin/activate
pip install -e .
```

### 2. Configure

**Environment setup:**

```bash
# Copy and edit environment variables
cp .env.example .env
vim .env  # Add your Jira/GitHub tokens (see Configuration section)

# CLI only: load environment variables
source .env
```

**Report configuration:**

```bash
# Copy config templates
cp config/jira_report_config.yaml.example config/jira_report_config.yaml
cp config/pr_report_config.yaml.example config/pr_report_config.yaml

# Edit to customize team members, phases, and metrics
vim config/jira_report_config.yaml
vim config/pr_report_config.yaml
```

> **Note:** Config templates (`.example` files) are provided in the repository. Your local config files will be ignored by git to keep your team-specific settings private.

### 3. Run

**CLI:**
```bash
ai-impact-analysis verify
ai-impact-analysis full
```

**Docker:**
```bash
# Docker commands = "docker-compose run ai-impact-analysis" + CLI command
docker-compose run ai-impact-analysis verify
docker-compose run ai-impact-analysis full
```

> **Tip:** Run `docker-compose up help` to see all available commands and usage examples.

## Configuration

### Environment Variables

Create `.env` file from template and add your credentials:

**Environment Variables Reference:**

| Variable                  | Required         | Purpose                                                                     | Example                                        |
| ------------------------- | ---------------- | --------------------------------------------------------------------------- | ---------------------------------------------- |
| `JIRA_URL`                | For Jira reports | Jira instance URL                                                           | `https://issues.redhat.com`                    |
| `JIRA_API_TOKEN`          | For Jira reports | Jira API authentication token                                               | `your_api_token_here`                          |
| `JIRA_PROJECT_KEY`        | For Jira reports | Jira project name/key                                                       | `Your Project Name`                            |
| `GITHUB_TOKEN`            | For PR reports   | GitHub personal access token                                                | `ghp_xxxxxxxxxxxx`                             |
| `GITHUB_REPO_OWNER`       | For PR reports   | GitHub repository owner/org                                                 | `your-org-name`                                |
| `GITHUB_REPO_NAME`        | For PR reports   | GitHub repository name                                                      | `your-repo-name`                               |
| `GOOGLE_CREDENTIALS_FILE` | Optional         | Path to Google service account JSON                                         | `/path/to/credentials.json`                    |
| `GOOGLE_SPREADSHEET_ID`   | Optional         | Google Sheets ID for auto-upload                                            | `1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms` |
| `ANTHROPIC_API_KEY`       | Optional         | Anthropic API key for AI-powered analysis (required for Docker AI analysis) | `sk-ant-...`                                   |

**Loading Variables:**

- **Docker**: Automatically loaded by `docker-compose`
- **CLI**: Run `source .env` before commands. Verify with `echo $JIRA_URL`

### Report Configuration

Configure analysis phases and team members in YAML config files: `config/jira_report_config.yaml` and `config/pr_report_config.yaml`

**Default Setup (Single Team):**

By default, the tool uses:
- Config files: `config/jira_report_config.yaml`, `config/pr_report_config.yaml`
- Output directories: `reports/jira/`, `reports/github/`
- Environment: `.env` file

Simply edit the config files in the `config/` directory with your team's information.

#### Configuration Options

**1. Phases** - Define analysis periods (required):

```yaml
phases:
  - name: "Before AI"
    start: "2024-01-01"
    end: "2024-06-30"
  - name: "With AI Tools"
    start: "2024-07-01"
    end: "2024-12-31"
```

**2. Team Members** - For individual reports (optional):

```yaml
# Jira config
team_members:
  - member: alice
    email: alice@company.com
    leave_days: 10      # or [10, 5] per phase
    capacity: 1.0       # 1.0 = full time, or [1.0, 0.5] per phase

# PR config
team_members:
  - name: alice-github
  - name: bob-github
```

**3. Default Assignee/Author** - Team vs individual (optional):

```yaml
default_assignee: ""  # "" = team reports, "email@company.com" = individual
default_author: ""    # "" = team reports, "username" = individual (PR config)
```

**4. Output Directory** - Customize report location (optional):

```yaml
# Jira config
output_dir: "reports/jira"              # Default
output_dir: "reports/team-a/jira"       # Team-specific

# PR config
output_dir: "reports/github"            # Default
output_dir: "reports/team-a/github"     # Team-specific
```

Essential for multi-team setups to isolate reports. If not specified, uses default directories.

**Note:** If you only need Jira metrics, configure only Jira-related files. Same for PR metrics.

#### Advanced: Custom Config Paths

**Option 1: Custom Config File**

Create your own config file and pass it with `--config`:

```bash
ai-impact-analysis jira full --config my-custom-config.yaml
```

Your custom file will be merged with defaults from `config/` directory.

**Option 2: Multi-Team Setup (Enterprise)**

For organizations managing multiple teams, use separate config directories:

```bash
# Team A
ai-impact-analysis full --config config/team-a
docker-compose --env-file .env.team-a run ai-impact-analysis full --config /app/config/team-a

# Team B
ai-impact-analysis full --config config/team-b
docker-compose --env-file .env.team-b run ai-impact-analysis full --config /app/config/team-b
```

**Multi-team isolation achieved through:**
- **Config directories**: `config/team-a/`, `config/team-b/` (each with `jira_report_config.yaml` and `pr_report_config.yaml`)
- **Environment files**: `.env.team-a`, `.env.team-b` (team-specific credentials)
- **Output directories**: Configure `output_dir: "reports/team-a/jira"` in each team's config files

➡️ **For complete configuration guide including multi-team setup, automation scripts, and best practices, see [docs/CONFIGURATION.md](docs/CONFIGURATION.md)**

## Usage Examples

**⚠️ Complete [Configuration](#configuration) section first.**

### Basic Commands

**Verify setup:**

```bash
ai-impact-analysis verify
```

**Generate reports:**

```bash
ai-impact-analysis full                              # ALL reports (Jira + PR)
ai-impact-analysis jira full                         # Jira: Team + Members + Combined
ai-impact-analysis pr full                           # PR: Team + Members + Combined
ai-impact-analysis jira team                         # Jira team report only
ai-impact-analysis pr team                           # PR team report only
ai-impact-analysis jira member alice@company.com     # Jira for one member
ai-impact-analysis pr member alice-github            # PR for one member (GitHub username)
```

**Advanced usage with options:**

```bash
ai-impact-analysis full --with-claude-insights --claude-api-mode
ai-impact-analysis jira full --no-upload
ai-impact-analysis pr team --incremental
ai-impact-analysis pr member testcara --incremental --no-upload

# With custom config files (all commands support --config)
ai-impact-analysis jira full --config config/team-a/jira_report_config.yaml
ai-impact-analysis pr full --config config/team-a/pr_report_config.yaml
ai-impact-analysis pr team --config config/team-a/pr_report_config.yaml --no-upload
ai-impact-analysis pr member alice --config config/my-team/pr_report_config.yaml
```

**Docker usage:**

```bash
# Just prefix CLI commands with "docker-compose run ai-impact-analysis"
docker-compose run ai-impact-analysis verify
docker-compose run ai-impact-analysis full
docker-compose run ai-impact-analysis jira full --no-upload
docker-compose run ai-impact-analysis pr member testcara --incremental
```

**Workflow:**

The `full` command workflow: Get metrics → Generate reports → Upload reports

- When `jira` or `pr` is specified, the workflow applies only to that report type
- `--no-upload` - Skip the Google Sheets upload process
- `--incremental` - Fetch only new PRs (cache enabled by default for performance, PR reports only)
- `--rest-api` - Use REST API instead of GraphQL for Jira metrics (default: GraphQL, ~30% faster)

### Output Files

**Jira Reports:**

- `reports/jira_report_general_*.txt` - Phase reports
- `reports/comparison_report_general_*.tsv` - Comparison table
- `reports/combined_jira_report_*.tsv` - Combined view

**PR Reports:**

- `reports/github/pr_report_general_*.txt` - Phase reports
- `reports/github/pr_comparison_general_*.tsv` - Comparison table
- `reports/github/combined_pr_report_*.tsv` - Combined view

**Note:** AI-powered analysis reports are listed separately in the [AI-Powered Analysis](#ai-powered-analysis-experimental) section.

## AI-Powered Analysis (Experimental)

> **⚠️ EXPERIMENTAL** - Optional feature for automated insights generation

Analyze your TSV reports with Claude to extract insights, trends, and actionable recommendations.

### Prerequisites & Setup

Choose **ONE** of the following methods:

#### Option 1: Claude Code CLI (CLI only, NOT Docker)

```bash
# Install Claude Code CLI (one-time setup)
curl -fsSL https://claude.ai/install.sh | bash

# Login to authenticate (interactive, requires browser)
claude login
```

**Note:** Claude Code CLI cannot be used inside Docker containers due to interactive authentication requirements.

#### Option 2: Anthropic API (Works with Docker & CLI)

```bash
# 1. Get API key from https://console.anthropic.com/
# 2. Add to .env file
echo "ANTHROPIC_API_KEY=sk-ant-your_api_key_here" >> .env

# 3. For CLI: reload environment
source .env

# 4. For Docker: environment is auto-loaded from .env
```

### Usage

#### Automatic with Full Workflow (Recommended)

**With Claude Code CLI (CLI only):**

```bash
# Requires Claude Code CLI installation (see Prerequisites)
ai-impact-analysis jira full --with-claude-insights
ai-impact-analysis pr full --with-claude-insights
ai-impact-analysis full --with-claude-insights
```

**With Anthropic API (CLI or Docker):**

```bash
# CLI - Requires ANTHROPIC_API_KEY in .env
ai-impact-analysis full --with-claude-insights --claude-api-mode
ai-impact-analysis jira full --with-claude-insights --claude-api-mode
ai-impact-analysis pr full --with-claude-insights --claude-api-mode

# Docker - Same commands, just add prefix
docker-compose run ai-impact-analysis full --with-claude-insights --claude-api-mode
```

#### Manual Script Execution (For existing reports)

**With Claude Code CLI (CLI only):**

```bash
# Analyze existing reports (requires Claude Code CLI installed)
python -m ai_impact_analysis.scripts.analyze_with_claude_code \
  --report "reports/jira/combined_jira_report_*.tsv"

python -m ai_impact_analysis.scripts.analyze_with_claude_code \
  --report "reports/github/combined_pr_report_*.tsv"
```

**With Anthropic API (CLI or Docker):**

```bash
# CLI
python -m ai_impact_analysis.scripts.analyze_with_claude_code \
  --report "reports/jira/combined_jira_report_*.tsv" \
  --claude-api-mode

# Docker - Same command, just add prefix
docker-compose run ai-impact-analysis \
  python -m ai_impact_analysis.scripts.analyze_with_claude_code \
  --report "reports/jira/combined_jira_report_*.tsv" \
  --claude-api-mode
```

### Output Files

AI analysis generates the following reports:

- `reports/ai_analysis_jira_*.txt` - AI insights for Jira metrics
- `reports/ai_analysis_pr_*.txt` - AI insights for PR metrics

### What You Get

- **Executive Summary**: Overall AI impact assessment
- **Key Trends**: 3-5 insights on metric changes
- **Bottlenecks & Risks**: Critical issues and patterns
- **Actionable Recommendations**: Concrete steps with measurable goals
- **AI Tool Impact**: ROI evaluation and effectiveness
- **Auto-upload**: Results to Google Sheets (optional with `--no-upload`)

**Customize analysis:**
Edit `config/analysis_prompt_template.yaml` to customize sections, output format, and focus areas.

## Understanding Metrics

> **Quick Reference** - For detailed explanations, formulas, and interpretation guidelines, see **[docs/METRICS_GUIDE.md](docs/METRICS_GUIDE.md)**

### GitHub PR Metrics

- **Total PRs** - Number of pull requests
- **AI Adoption Rate** - Percentage of PRs with AI assistance
- **Time to Merge** - Average time from PR creation to merge
- **Time to First Review** - Average time until first review
- **Changes Requested** - Average number of change requests per PR
- **Reviewers & Comments** - Average reviewers and comments (excluding bots)
- **Lines Changed & Files Modified** - Code change volume

### Jira Metrics

- **Total Issues** - Number of issues closed
- **Average Closure Time** - Time from creation to resolution
- **Daily Throughput** - Issues closed per working day (4 calculation variants)
- **State Time** - Average time in each state (New, To Do, In Progress, Review, Waiting)
- **Re-entry Rates** - How often issues return to previous states (measures rework)
- **Issue Type Distribution** - Breakdown by type (Bug, Story, Task, etc.)

### Positive AI Impact Indicators

- ✅ **Decreased** Time to Merge / Closure Time
- ✅ **Decreased** Changes Requested
- ✅ **Increased** Daily Throughput
- ✅ **Decreased** Re-entry Rates (less rework)

➡️ **For detailed metric explanations, calculation formulas, and interpretation guidelines**, see **[docs/METRICS_GUIDE.md](docs/METRICS_GUIDE.md)**

## Documentation & Contributing

### For Users

- **[Configuration Guide](docs/CONFIGURATION.md)** - Complete configuration reference including Google Sheets, custom configs, multi-team setup, environment variables, and best practices
- **[Metrics Guide](docs/METRICS_GUIDE.md)** - Detailed metric explanations, calculation formulas, interpretation guidelines

### For Contributors

- **[Contributing Guide](docs/CONTRIBUTING.md)** - Development setup, commit guidelines, testing, code quality, pull requests

## Support

**Get help:**

- Issues: https://github.com/testcara/ai_impact_analysis/issues
- Documentation: See `docs/` directory
- Command help: `ai-impact-analysis --help`

## License

This project is licensed under the MIT License.
