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

- **Measure AI Productivity Impact**: Compare development efficiency before and after AI tool adoption with objective metrics
- **Enable Objective Performance Reviews**: Data-driven evaluation for teams and individuals based on metrics, not opinions
- **Make Informed Decisions**: Track closure time, merge time, throughput, and trends to identify bottlenecks and opportunities
- **Visualize Team Performance**: Auto-generated box plot charts show distribution and outliers, embedded in Google Sheets for stakeholder review
- **Support Multi-Team Analysis**: Aggregate reports across multiple repositories/projects for organization-wide insights
- **Protect Privacy**: Automatic anonymization in CI environments with optional email notifications for members to find their metrics
- **Enable Easy Sharing**: Auto-upload to Google Sheets with embedded visualizations for team and stakeholder visibility
- **Deploy Flexibly**: GitHub Actions CI (zero setup) or local CLI for full control and data access

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
│                         CLI Interface                           │
│                         (impactlens)                            │
└──────────────┬──────────────────────────────┬───────────────────┘
               │                              │
       ┌───────▼────────┐            ┌────────▼──────────┐
       │  Jira Workflow │            │   PR Workflow     │
       └───────┬────────┘            └────────┬──────────┘
               │                              │
  ┌────────────▼──────────────┐  ┌────────────▼───────────────────┐
  │ Jira Client(REST/GraphQL) │  │ GitHub/GitLab Client (GraphQL) │
  └────────────┬──────────────┘  └────────────┬───────────────────┘
               │                              │
               └───────────────┬──────────────┘
                               │
                  ┌────────────▼───────────┐
                  │   Metrics Calculators  │
                  └────────────┬───────────┘
                               │
                  ┌────────────▼───────────┐
                  │   Report Generators    │
                  └────────────┬───────────┘
                               │
               ┌───────────────▼───────────────┐
               │  Visualization Generators     │
               └───────────────┬───────────────┘
                               │
                  ┌────────────▼───────────┐
                  │   Report Aggregators   │
                  └────────────┬───────────┘
                               │
           ┌───────────────────┼─────────────────────────┐
           │                   │                         │
     ┌─────▼─────┐ ┌───────────▼──────────┐ ┌────────────▼──────────────┐
     │ TSV Files │ │ PNG Charts(Optional) │ │ Gemini Analysis(Optional) │
     └─────┬─────┘ └───────────┬──────────┘ └────────────┬──────────────┘
           │                   │                         │
           └───────────────────┼─────────────────────────┘
                               │
┌──────────────────────────────▼─────────────────────────────────────┐
│ Google Sheets Reports with optional embeded Charts and AI insights │
└────────────────────────────────────────────────────────────────────┘
```

**Key Components:**

- **CLI Interface**: Unified command-line interface (`cli.py`)
- **Clients**: API integrations (Jira REST/GraphQL, GitHub/GitLab GraphQL, Google Sheets)
- **Core Logic**: Metrics calculators and report generators
- **Visualization**: Box plot chart generation, GitHub image storage, Google Sheets embedding
- **Output**: TSV reports, visual charts, Google Sheets dashboards, AI-powered insights

**For detailed directory structure**, see [Contributing Guide - Project Structure](docs/CONTRIBUTING.md#project-structure)

## Quick Start

### ⚡ GitHub Actions CI (Recommended)

**Perfect for:** Teams wanting automated reports with zero local setup and privacy protection.

> 🔒 **Privacy Protection**: CI automatically anonymizes individual data (names → Developer-A3F2, hides emails/leave_days/capacity).
>
> 📧 **Find Your Metrics**: Enable `email_anonymous_id: true` in config to receive your hash ID via email and locate your data in anonymized reports.

➡️ **See [Configuration Guide](docs/CONFIGURATION.md)** for complete setup instructions

---

### 💻 Local Development

**Perfect for:** Developers who prefer local execution, need offline access, or want to customize workflows.

➡️ **See [Local Development Guide](docs/LOCAL_DEVELOPMENT.md)** for setup and usage

## Configuration

ImpactLens supports two configuration scenarios:

| Scenario    | Team Structure          | Reports Generated            |
| ----------- | ----------------------- | ---------------------------- |
| **Simple**  | Single project/repo     | TEAM + COMBINED              |
| **Complex** | Multiple projects/repos | TEAM + COMBINED + AGGREGATED |

**Configuration includes:**

- Jira/GitHub/GitLab project settings (unified environment variables)
- Analysis periods (phases)
- Team member definitions
- Privacy & anonymization options
- Multi-repo aggregation setup
- Google Sheets integration
- Email notification settings
- SSL certificate verification (for self-signed certificates)

**➡️ See [Configuration Guide](docs/CONFIGURATION.md)** for complete setup instructions and examples

## AI-Powered Analysis (Optional)

> **💡 OPTIONAL** - Get AI-powered insights from your metrics reports

ImpactLens can automatically analyze your reports to extract insights on trends, bottlenecks, and actionable recommendations. AI analysis is **enabled by default** in CI workflows and can be disabled via `no_ai_analysis` config option.

**What you get:** Executive summary, key trends, bottlenecks & risks, actionable recommendations, and AI tool impact assessment.

**Usage:** Automatic with Gemini API key, or use generated prompts with ChatGPT/Claude/Gemini manually.

**➡️ For setup instructions and advanced options, see [Local Development Guide - AI Analysis](docs/LOCAL_DEVELOPMENT.md#ai-powered-analysis)**

## Understanding Metrics

> **Quick Reference** - For detailed explanations, formulas, and interpretation guidelines, see **[docs/METRICS_GUIDE.md](docs/METRICS_GUIDE.md)**

### GitHub PR Metrics

- **Total PRs** - Number of pull requests
- **AI Adoption Rate** - Percentage of PRs with AI assistance (detected via commit messages)
- **AI Tool Usage** - Count of PRs using different AI tools (Claude, Cursor, Copilot, etc.)
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

## Support

**Get help:**

- Issues: https://github.com/testcara/impactlens/issues
- Documentation: See `docs/` directory
- Command help: `impactlens --help`

## License

This project is licensed under the MIT License.
