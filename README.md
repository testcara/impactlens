# ImpactLens

A data-driven tool that delivers actionable insights for measuring AI coding assistant impact and enabling objective performance reviews through Jira and GitHub metrics analysis.

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

ImpactLens helps engineering leaders and teams measure the real-world impact of AI coding assistants by analyzing development metrics from Jira and GitHub. Get objective insights into productivity changes, team performance, and AI tool effectiveness.

**Business Value:**

- **Track AI Productivity Impact**: Compare development efficiency before and after AI tool adoption
- **Performance Reviews**: Objective metrics for evaluating team and individual performance
- **Data-Driven Insights**: Track closure time, merge time, throughput, and more to help making informed decisions
- **Privacy Protection**: Automatic anonymization in CI for sharing reports while protecting individual privacy
- **CI-Driven Automation**: Submit config via PR → Reports auto-generated and posted as PR comments
- **Multi-Repo Aggregation**: Combine reports from multiple repositories/projects into unified team-wide views
- **Easy Sharing**: Auto-upload to Google Sheets for stakeholder visibility
- **Flexible Deployment**: GitHub Actions CI (zero config) or local CLI for full data access

**Use Cases:**

- Engineering leaders evaluating AI tool investments
- Teams measuring productivity improvements
- Managers conducting objective performance reviews for teams and individuals
- Researchers studying AI coding assistant effectiveness
- Organizations tracking developer efficiency over time

## Architecture & Project Structure

### System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLI Interface                            │
│                         (impactlens)                             │
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
impactlens/
├── impactlens/           # Core library
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
│   │   ├── report_aggregator.py  # Multi-team aggregation
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
│       ├── anonymization.py      # Privacy & anonymization utilities
│       ├── workflow_utils.py     # Config loading & workflow helpers
│       └── report_utils.py       # Report generation utilities
├── .github/workflows/            # GitHub Actions CI
│   ├── ci.yml                    # Test & lint workflow
│   └── generate-reports.yml      # Automated report generation
├── config/                       # Configuration files
│   ├── jira_report_config.yaml.example  # Jira config template
│   ├── pr_report_config.yaml.example    # PR config template
│   ├── aggregation_config.yaml.example  # Multi-repo aggregation config
│   ├── analysis_prompt_template.yaml    # AI analysis prompts
│   ├── test-integration-ci/      # CI integration test configs
│   │   └── test-ci-team1/
│   │       ├── jira_report_config.yaml
│   │       └── pr_report_config.yaml
│   └── test-aggregation-ci/      # CI aggregation test configs
│       ├── aggregation_config.yaml
│       ├── test-ci-team1/
│       │   ├── jira_report_config.yaml
│       │   └── pr_report_config.yaml
│       └── test-ci-team2/
│           ├── jira_report_config.yaml
│           └── pr_report_config.yaml
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

### ⚡ GitHub Actions CI (Recommended - Zero Config)

**Perfect for:** Teams wanting automated reports with zero local setup and privacy protection.

1. **Clone & create team config**:
   ```bash
   git clone https://github.com/testcara/impactlens.git
   cd impactlens
   mkdir -p config/my-team
   cp config/*_config.yaml.example config/my-team/
   # Edit configs with your team settings
   ```

2. **Generate reports via PR**:
   ```bash
   git checkout -b report/my-team-2024-12
   git add -f config/my-team/
   git commit -m "chore: generate AI impact report for my-team"
   git push origin report/my-team-2024-12
   # Create PR → CI auto-generates reports → View in PR comments
   ```

3. **View anonymized reports**: Auto-uploaded to [Default Google Sheet](https://docs.google.com/spreadsheets/d/1AnX3zGoVOv9QXgx3ck2IH8ksRnBoW2V4Uk4o-KoyV0k/edit?gid=0#gid=0) or download from workflow artifacts

> 🔒 **Privacy Protection**: CI automatically anonymizes individual data (names → Developer-A3F2, hides emails/leave_days/capacity). For full data, run locally.
>
> **For custom Google Sheets**: Grant Editor access to `cara-google-sheet-sa@wlin-438107.iam.gserviceaccount.com`

---

### 💻 Local Development (Full Data Access)

For detailed individual data, run locally with Docker or CLI:

```bash
git clone https://github.com/testcara/impactlens.git
cd impactlens

# Docker (no Python needed)
cp .env.example .env && vim .env
docker-compose run impactlens full

# CLI (Python developers)
python3 -m venv venv && source venv/bin/activate
pip install -e . && cp .env.example .env && source .env
impactlens full
```

➡️ **For detailed configuration and advanced features**, see **[Configuration Guide](docs/CONFIGURATION.md)**

## Configuration

ImpactLens supports two configuration scenarios:

| Scenario | Team Structure | Reports Generated |
|----------|---------------|-------------------|
| **Simple** | Single project/repo | TEAM + COMBINED |
| **Complex** | Multiple projects/repos | TEAM + COMBINED + AGGREGATED |

**Quick Setup (Simple Scenario):**

1. Create config directory: `mkdir -p config/my-team`
2. Copy templates and edit with your team settings:
   - `project`: Jira project key or GitHub repo owner/name
   - `phases`: Analysis periods (e.g., before/after AI adoption)
   - `team_members`: Team scope with optional leave_days and capacity
3. Submit via PR → CI auto-generates reports

**For complete configuration guide including:**
- Detailed configuration examples for both scenarios
- Multi-repo aggregation setup
- Privacy & anonymization
- Environment variables
- Best practices & troubleshooting

**➡️ See [Configuration Guide](docs/CONFIGURATION.md)**

## Usage Examples

**⚠️ Complete [Configuration](#configuration) section first.**

### Basic Commands

**Verify setup:**

```bash
impactlens verify
```

**Generate reports:**

```bash
# Complete workflows
impactlens full                              # ALL reports (Jira + PR + Auto-aggregate if config exists)
impactlens jira full                         # Jira: Team + Members + Combined
impactlens pr full                           # PR: Team + Members + Combined

# Individual reports
impactlens jira team                         # Jira team report only
impactlens pr team                           # PR team report only
impactlens jira member alice@company.com     # Jira for one member
impactlens pr member alice-github            # PR for one member (GitHub username)

# Multi-repo aggregation (combine reports from multiple repositories/projects)
impactlens aggregate --config config/aggregation_config.yaml      # Aggregate both Jira and PR
impactlens agg --config config/aggregation_config.yaml            # Short alias
impactlens aggregate --config config/aggregation_config.yaml --jira-only   # Jira only
impactlens aggregate --config config/aggregation_config.yaml --pr-only     # PR only
```

**Advanced usage with options:**

```bash
# Privacy protection (anonymize individual names in combined reports)
impactlens full --hide-individual-names              # Names → Developer-A3F2, Developer-B7E1, etc.
impactlens jira full --hide-individual-names         # Also hides leave_days and capacity
impactlens pr full --hide-individual-names

# Upload control
impactlens full --upload-members                     # Upload ALL reports including members
impactlens jira full --no-upload                     # Skip all uploads
impactlens pr full --upload-members                  # Upload PR members reports

# With Claude insights
impactlens full --with-claude-insights --claude-api-mode

# Incremental PR fetching
impactlens pr team --incremental
impactlens pr member testcara --incremental --no-upload

# With custom config files (all commands support --config)
impactlens jira full --config config/team-a/jira_report_config.yaml
impactlens pr full --config config/team-a/pr_report_config.yaml --upload-members
impactlens pr team --config config/team-a/pr_report_config.yaml --no-upload
impactlens pr member alice --config config/my-team/pr_report_config.yaml
```

**Docker usage:**

```bash
# Just prefix CLI commands with "docker-compose run impactlens"
docker-compose run impactlens verify
docker-compose run impactlens full
docker-compose run impactlens full --upload-members              # Upload all including members
docker-compose run impactlens jira full --no-upload
docker-compose run impactlens pr member testcara --incremental
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

**Aggregated Reports** (in custom `output_dir` from aggregation config, for multi-repo teams):

- `aggregated_jira_report_*.tsv` - Unified Jira metrics across all repositories
- `aggregated_pr_report_*.tsv` - Unified PR metrics across all repositories

**Note:**

- `{project}` prefix is added when `jira_project_key` or `github_repo_name` is configured
- Aggregated reports are generated only when `aggregation_config.yaml` is present
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

# 3. For CLI: activate venv (if using) and reload environment
source venv/bin/activate  # If using virtual environment
source .env

# 4. For Docker: environment is auto-loaded from .env
```

### Usage

#### Automatic with Full Workflow (Recommended)

**With Claude Code CLI (CLI only):**

```bash
# Requires Claude Code CLI installation (see Prerequisites)
impactlens jira full --with-claude-insights
impactlens pr full --with-claude-insights
impactlens full --with-claude-insights
```

**With Anthropic API (CLI or Docker):**

```bash
# CLI - Requires ANTHROPIC_API_KEY in .env
impactlens full --with-claude-insights --claude-api-mode
impactlens jira full --with-claude-insights --claude-api-mode
impactlens pr full --with-claude-insights --claude-api-mode

# Docker - Same commands, just add prefix
docker-compose run impactlens full --with-claude-insights --claude-api-mode
```

#### Manual Script Execution (For existing reports)

**With Claude Code CLI (CLI only):**

```bash
# Analyze existing reports (requires Claude Code CLI installed)
python -m impactlens.scripts.analyze_with_claude_code \
  --report "reports/jira/combined_jira_report_*.tsv"

python -m impactlens.scripts.analyze_with_claude_code \
  --report "reports/github/combined_pr_report_*.tsv"
```

**With Anthropic API (CLI or Docker):**

```bash
# CLI
python -m impactlens.scripts.analyze_with_claude_code \
  --report "reports/jira/combined_jira_report_*.tsv" \
  --claude-api-mode

# Docker - Same command, just add prefix
docker-compose run impactlens \
  python -m impactlens.scripts.analyze_with_claude_code \
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
- **AI Tool Impact**: Productivity impact assessment and effectiveness analysis
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

## Next Steps

- **Validation & Testing**: Expand usage with diverse teams/organizations to validate product value
- **Unified Data Platform**: Migrate to centralized data warehouse (e.g., Snowflake) to consolidate metrics from multiple sources (Jira, GitHub, GitLab, Slacks, etc.)
- **Enhanced Metrics**: Add more metrics and industry benchmarks and percentile rankings for peer comparison
- **AI-Powered Insights**: Expand beyond Claude to support multiple AI providers (OpenAI, Gemini, etc.), customizable analysis templates, and interactive analysis interface
- **Visualization**: Build interactive dashboard for better insights and executive reporting

## Support

**Get help:**

- Issues: https://github.com/testcara/impactlens/issues
- Documentation: See `docs/` directory
- Command help: `impactlens --help`

## License

This project is licensed under the MIT License.
