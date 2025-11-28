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

```bash
# Docker
docker-compose run --rm ai-impact-analysis verify
docker-compose run --rm ai-impact-analysis full

# CLI
ai-impact-analysis verify
ai-impact-analysis full
```

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

Configure analysis phases and team members in YAML config files.
Files: `config/jira_report_config.yaml` and `config/pr_report_config.yaml`

#### Phases Configuration

Define analysis phases (customize for your AI adoption timeline). You can define as many analysis periods as needed (dates in YYYY-MM-DD format).

```yaml
phases:
  - name: "Before AI"
    start: "2024-01-01"
    end: "2024-06-30"
  - name: "With AI Tools"
    start: "2024-07-01"
    end: "2024-12-31"
```

#### Default Assignee/Author Configuration (Optional)

For `config/jira_report_config.yaml`:

```yaml
# "" = team reports, "email@company.com" = individual reports
default_assignee: ""
```

For `config/pr_report_config.yaml`:

```yaml
# "" = team reports, "username" = individual reports
default_author: ""
```

#### Team Members Configuration (Optional, for --all-members mode)

For `config/jira_report_config.yaml`:

```yaml
team_members:
  - member: alice
    email: alice@company.com
    leave_days: 10 # Total leave days, or [10, 5] per phase
    capacity: 1.0 # 1.0 = full time, 0.8 = 80%, or [1.0, 0.5] per phase
  - member: bob
    email: bob@company.com
    leave_days: [5, 8] # Different per phase
    capacity: [1.0, 0.0] # Left team in phase 2
```

For `config/pr_report_config.yaml`:

```yaml
# Team members (GitHub usernames)
team_members:
  - name: alice-github
  - name: bob-github
```

**Note:** If you only need Jira metrics, configure only Jira-related environment variables and config files. Same for PR metrics.

#### Custom Configuration Files

You can update the existing config files, or create custom YAML files and use the `--config` flag:

```bash
ai-impact-analysis jira full --config my-custom-config.yaml
```

**Note:** In your customized files, you don't need to specify all items mentioned above. Your customized files will be merged with the default config files in the `config/` directory.

## Usage Examples

**⚠️ Complete [Configuration](#configuration) section first.**

### Basic Commands

**Verify setup:**

```bash
# Docker
docker-compose run --rm ai-impact-analysis verify

# CLI
ai-impact-analysis verify
```

**Generate reports:**

```bash
# Docker - get all reports
docker-compose run --rm ai-impact-analysis full
# Docker - get reports for Jira metrics
docker-compose run --rm ai-impact-analysis jira full
# Docker - get reports for PR metrics
docker-compose run --rm ai-impact-analysis pr full

# CLI
ai-impact-analysis full        # ALL reports (Jira + PR team reports + individual reports + combined reports)

# If you would like to get reports in steps:
ai-impact-analysis jira full   # Jira: Team + Members + Combined
ai-impact-analysis pr full     # PR: Team + Members + Combined
ai-impact-analysis jira team   # Jira team report
ai-impact-analysis pr team     # PR team report
ai-impact-analysis jira member alice@company.com   # Jira for one member
ai-impact-analysis pr member alice-github          # PR for one member (GitHub username)
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

**CLI with Claude Code CLI (default):**

```bash
# Requires Claude Code CLI installation (see Prerequisites)
ai-impact-analysis jira full --with-claude-insights
ai-impact-analysis pr full --with-claude-insights
ai-impact-analysis full --with-claude-insights
```

**CLI with Anthropic API:**

```bash
# Requires ANTHROPIC_API_KEY in .env
ai-impact-analysis jira full --with-claude-insights --claude-api-mode
ai-impact-analysis pr full --with-claude-insights --claude-api-mode
ai-impact-analysis full --with-claude-insights --claude-api-mode
```

**Docker (requires Anthropic API):**

```bash
# Requires ANTHROPIC_API_KEY in .env
docker-compose run --rm ai-impact-analysis jira full --with-claude-insights --claude-api-mode
docker-compose run --rm ai-impact-analysis pr full --with-claude-insights --claude-api-mode
docker-compose run --rm ai-impact-analysis full --with-claude-insights --claude-api-mode
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

**With Anthropic API:**

```bash
# CLI
python -m ai_impact_analysis.scripts.analyze_with_claude_code \
  --report "reports/jira/combined_jira_report_*.tsv" \
  --claude-api-mode

# Docker
docker-compose run --rm ai-impact-analysis \
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

- **[Configuration Guide](docs/CONFIGURATION.md)** - Google Sheets integration, custom config files, environment variables
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
