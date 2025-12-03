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
│   │   ├── jira_client.py        # Jira REST/GraphQL API
│   │   ├── github_client_graphql.py  # GitHub GraphQL
│   │   └── sheets_client.py      # Google Sheets API
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
│   │   ├── generate_*_comparison_report.py
│   │   ├── upload_to_sheets.py
│   │   └── verify_setup.py
│   └── utils/                    # Shared utilities
│       ├── workflow_utils.py     # Config loading & workflow helpers
│       └── report_utils.py       # Report generation utilities
├── .github/workflows/            # GitHub Actions CI
│   ├── ci.yml                    # Test & lint workflow
│   └── generate-reports.yml      # Automated report generation
├── config/                       # Configuration files
│   ├── jira_report_config.yaml.example  # Jira config template
│   ├── pr_report_config.yaml.example    # PR config template
│   ├── analysis_prompt_template.yaml    # AI analysis prompts
│   ├── team-a/                   # Team-specific configs (multi-team)
│   │   ├── jira_report_config.yaml
│   │   └── pr_report_config.yaml
│   └── team-b/                   # Another team (example)
│       ├── jira_report_config.yaml
│       └── pr_report_config.yaml
├── docs/                         # Documentation
│   ├── CONFIGURATION.md          # Detailed configuration guide
│   ├── METRICS_GUIDE.md          # Metrics explanations & formulas
│   └── CONTRIBUTING.md           # Contribution guidelines
├── tests/                        # Test suite
├── reports/                      # Generated reports (gitignored)
│   ├── jira/                     # Jira reports
│   └── github/                   # PR reports
├── .env.example                  # Environment variables template
├── docker-compose.yml            # Docker Compose setup
├── Dockerfile                    # Docker build configuration
├── pyproject.toml                # Project metadata & CLI config
└── tox.ini                       # Test configuration
```

## Quick Start

### ⚡ Option 1: GitHub Actions CI (Recommended)

**Perfect for:** Teams wanting automated reports with zero local setup.

**Prerequisites:** GitHub repository access only - CI pre-configured!

1. **Clone & create team config**:
   ```bash
   git clone https://github.com/testcara/ai_impact_analysis.git
   cd ai_impact_analysis
   mkdir -p config/my-team
   cp config/*_config.yaml.example config/my-team/
   # Edit configs with your team settings
   ```

2. **Generate reports via PR**:
   ```bash
   git checkout -b report/my-team-2024-12
   git add config/my-team/
   git commit -m "chore: generate AI impact report for my-team"
   git push origin report/my-team-2024-12
   # Create PR → CI auto-generates reports → View in PR comments
   ```

3. **View reports**:
   - Auto-uploads to [Default Google Sheet](https://docs.google.com/spreadsheets/d/1AnX3zGoVOv9QXgx3ck2IH8ksRnBoW2V4Uk4o-KoyV0k/edit?gid=0#gid=0)
   - Download from workflow artifacts
   - **Manually close PR** after reviewing (DO NOT MERGE config-only PRs)

> **Note:** Uses default credentials. For custom credentials/sheets, see [Configuration Guide](docs/CONFIGURATION.md)

---

### 💻 Option 2: Local Development (Docker or CLI)

**For local development and testing**:

```bash
git clone https://github.com/testcara/ai_impact_analysis.git
cd ai_impact_analysis

# Docker (no Python needed)
cp .env.example .env && vim .env
docker-compose run ai-impact-analysis full

# CLI (Python developers)
pip install -e . && cp .env.example .env && source .env
ai-impact-analysis full
```

➡️ **For detailed local setup, multi-team configuration, and Google Sheets integration**, see **[Configuration Guide](docs/CONFIGURATION.md)**

## Configuration

### Quick Configuration Guide

**Configuration priority**: YAML Config (non-sensitive) → Environment Variables (credentials) → CI Defaults

**Essential setup**:

1. **Phases** (YAML) - Define before/after AI periods:
   ```yaml
   phases:
     - name: "Before AI"
       start: "2024-01-01"
       end: "2024-06-30"
     - name: "With AI"
       start: "2024-07-01"
       end: "2024-12-31"
   ```

2. **Credentials** (.env) - API tokens and passwords:
   ```bash
   cp .env.example .env
   # Add: JIRA_API_TOKEN, GITHUB_TOKEN, etc.
   ```

3. **Team members** (YAML, optional) - For individual reports:
   ```yaml
   team_members:
     - member: alice
       email: alice@company.com
   ```

➡️ **For complete configuration reference including:**
- Multi-team setup & isolation
- Google Sheets integration
- Custom config paths
- Environment variables reference
- Best practices & troubleshooting

**See [Configuration Guide](docs/CONFIGURATION.md)**

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
# Upload control
ai-impact-analysis full --upload-members                     # Upload ALL reports including members
ai-impact-analysis jira full --no-upload                     # Skip all uploads
ai-impact-analysis pr full --upload-members                  # Upload PR members reports

# With Claude insights
ai-impact-analysis full --with-claude-insights --claude-api-mode

# Incremental PR fetching
ai-impact-analysis pr team --incremental
ai-impact-analysis pr member testcara --incremental --no-upload

# With custom config files (all commands support --config)
ai-impact-analysis jira full --config config/team-a/jira_report_config.yaml
ai-impact-analysis pr full --config config/team-a/pr_report_config.yaml --upload-members
ai-impact-analysis pr team --config config/team-a/pr_report_config.yaml --no-upload
ai-impact-analysis pr member alice --config config/my-team/pr_report_config.yaml
```

**Docker usage:**

```bash
# Just prefix CLI commands with "docker-compose run ai-impact-analysis"
docker-compose run ai-impact-analysis verify
docker-compose run ai-impact-analysis full
docker-compose run ai-impact-analysis full --upload-members              # Upload all including members
docker-compose run ai-impact-analysis jira full --no-upload
docker-compose run ai-impact-analysis pr member testcara --incremental
```

**Workflow:**

The `full` command workflow: Get metrics → Generate reports → Upload reports

- When `jira` or `pr` is specified, the workflow applies only to that report type
- `--no-upload` - Skip all Google Sheets uploads
- `--upload-members` - Upload individual member reports (default: only team and combined reports are uploaded)
- `--incremental` - Fetch only new PRs (cache enabled by default for performance, PR reports only)
- `--rest-api` - Use REST API instead of GraphQL for Jira metrics (default: GraphQL, ~30% faster)

**Upload Behavior:**
- **Default**: Only team and combined reports are uploaded to Google Sheets
- **Member reports**: Not uploaded by default (to save quota), use `--upload-members` to enable

### Output Files

**Jira Reports** (in `reports/jira/` or custom `output_dir`):

- `jira_report_general_*.txt` - Phase reports (detailed metrics)
- `jira_comparison_general_*.tsv` - Comparison table (phases side-by-side)
- `{project}_combined_jira_report_*.tsv` - Combined view (all members grouped by metric)

**PR Reports** (in `reports/github/` or custom `output_dir`):

- `pr_report_general_*.txt` - Phase reports (detailed metrics)
- `pr_comparison_general_*.tsv` - Comparison table (phases side-by-side)
- `{project}_combined_pr_report_*.tsv` - Combined view (all members grouped by metric)

**Note:**
- `{project}` prefix is added when `jira_project_key` or `github_repo_name` is configured
- AI-powered analysis reports are listed separately in the [AI-Powered Analysis](#ai-powered-analysis-experimental) section

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
