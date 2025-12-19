# ImpactLens

A data-driven tool that delivers actionable insights for measuring AI coding assistant impact and enabling objective performance reviews through Jira, GitHub, and GitLab metrics analysis.

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

ImpactLens helps engineering leaders and teams measure the real-world impact of AI coding assistants by analyzing development metrics from Jira, GitHub, and GitLab. Get objective insights into productivity changes, team performance, and AI tool effectiveness.

**Business Value:**

- **Track AI Productivity Impact**: Compare development efficiency before and after AI tool adoption
- **Performance Reviews**: Objective metrics for evaluating team and individual performance
- **Data-Driven Insights**: Track closure time, merge time, throughput, and more to help making informed decisions
- **Privacy Protection**: Automatic anonymization in CI for sharing reports while protecting individual privacy. Optional email notifications send members their anonymous ID to find personal metrics
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
       │  Jira Client   │            │ GitHub/GitLab     │
       │  (REST/GraphQL)│            │ Client (GraphQL)  │
       └───────┬────────┘            └────────┬──────────┘
               │                              │
               └──────────┬───────────────────┘
                          │
                 ┌────────▼───────────┐
                 │  Metrics           │
                 │  Calculators       │
                 └────────┬───────────┘
                          │
                 ┌────────▼───────────┐
                 │  Report            │
                 │  Generators        │
                 └────────┬───────────┘
                          │
                 ┌────────▼───────────┐
                 │  Report            │
                 │  Aggregators       │
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
- **Clients**: API integrations (Jira REST/GraphQL, GitHub/GitLab GraphQL, Google Sheets)
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

| Scenario    | Team Structure          | Reports Generated            |
| ----------- | ----------------------- | ---------------------------- |
| **Simple**  | Single project/repo     | TEAM + COMBINED              |
| **Complex** | Multiple projects/repos | TEAM + COMBINED + AGGREGATED |

**Quick Setup (Simple Scenario):**

1. Create config directory: `mkdir -p config/my-team`
2. Copy templates and edit with your team settings:
   - `project`: Jira project key or GitHub/GitLab repo (owner/name format)
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

## AI-Powered Analysis (Optional)

> **💡 OPTIONAL** - Get actionable insights from your metrics reports using AI
>
> **⚠️ CURRENT LIMITATION**: AI analysis prompts currently support **simple scenarios only** (single project/repo). Aggregated reports from complex scenarios (multi-project/repos) are not yet supported.

Use AI to analyze your generated reports and extract insights on trends, bottlenecks, and actionable recommendations.

### What You Get

- **Executive Summary** - Overall AI impact assessment
- **Key Trends** - 3-5 critical insights on metric changes
- **Bottlenecks & Risks** - Issues and patterns requiring attention
- **Actionable Recommendations** - Concrete steps with measurable goals
- **AI Tool Impact** - Productivity assessment and effectiveness analysis

### Usage Options (Pick One)

**Option 1: Use Generated Prompts (Easiest - No Setup)**

Reports are generated with ready-to-use AI analysis prompts:

1. Download prompt files from PR artifacts or `reports/` folder:
   - `ai_analysis_jira_prompt_*.txt` - Jira analysis prompt
   - `ai_analysis_pr_prompt_*.txt` - PR analysis prompt
2. Copy prompt content and paste into any AI:
   - Claude (https://claude.ai)
   - ChatGPT (https://chat.openai.com)
   - Gemini (https://gemini.google.com)
3. Get instant insights - no need to write your own prompts!

**Option 2: Claude Code CLI (Interactive - Recommended for Deep Analysis)**

```bash
# Install Claude Code CLI (one-time)
curl -fsSL https://claude.ai/install.sh | bash
claude login

# Generate reports with interactive AI analysis
impactlens full --with-claude-insights
```

Benefits: Interactive discussion, iterative refinement, project-specific customization

**Option 3: Anthropic API (Automated)**

```bash
# Configure API key in .env
echo "ANTHROPIC_API_KEY=sk-ant-..." >> .env

# Generate reports with automated AI analysis
impactlens full --with-claude-insights --claude-api-mode
```

**➡️ For detailed setup and advanced options, see [Local Development Guide - AI Analysis](docs/LOCAL_DEVELOPMENT.md#ai-powered-analysis)**

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
- **[Local Development Guide](docs/LOCAL_DEVELOPMENT.md)** - CLI usage, Docker commands, advanced options for local development

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
