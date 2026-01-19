# Local Development Guide

This guide covers local CLI usage and Docker workflows for developers who want full data access or to run ImpactLens outside of CI/CD.

> **💡 Most users should use [GitHub Actions CI workflow](../README.md#-github-actions-ci-recommended---zero-config)** for automated report generation with zero local setup.

## Table of Contents

- [Quick Start](#quick-start)
  - [CLI Installation](#cli-installation)
  - [Docker Setup](#docker-setup)
- [Basic Commands](#basic-commands)
- [Advanced Usage](#advanced-usage)
- [Docker Usage](#docker-usage)
- [Workflow Details](#workflow-details)
- [Output Files](#output-files)
- [AI-Powered Analysis](#ai-powered-analysis)
- [Troubleshooting](#troubleshooting)

## Quick Start

### CLI Installation

**Prerequisites:**
- Python 3.9+
- Git

**Installation steps:**

```bash
git clone https://github.com/testcara/impactlens.git
cd impactlens

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in editable mode
pip install -e .

# Configure environment
cp .env.example .env
# Edit .env with your credentials (JIRA_TOKEN, GITHUB_TOKEN, etc.)
source .env

# Verify setup
impactlens verify
```

### Docker Setup

**Prerequisites:**
- Docker
- Docker Compose

**Installation steps:**

```bash
git clone https://github.com/testcara/impactlens.git
cd impactlens

# Configure environment
cp .env.example .env
# Edit .env with your credentials

# Verify setup
docker-compose run impactlens verify
```

## Basic Commands

**⚠️ Complete [Configuration Guide](CONFIGURATION.md) section first.**

### Verify Setup

```bash
impactlens verify
```

### Generate Reports

**Complete workflows:**

```bash
# ALL reports (Jira + PR + Auto-aggregate if config exists)
impactlens full

# Jira: Team + Members + Combined
impactlens jira full

# PR: Team + Members + Combined
impactlens pr full
```

**Individual reports:**

```bash
# Jira team report only
impactlens jira team

# PR team report only
impactlens pr team

# Jira for one member
impactlens jira member alice@company.com

# PR for one member (GitHub username)
impactlens pr member alice-github
```

**Multi-repo aggregation:**

```bash
# Aggregate both Jira and PR
impactlens aggregate --config config/aggregation_config.yaml

# Short alias
impactlens agg --config config/aggregation_config.yaml

# Jira only
impactlens aggregate --config config/aggregation_config.yaml --jira-only

# PR only
impactlens aggregate --config config/aggregation_config.yaml --pr-only
```

## Advanced Usage

### Privacy Protection

Anonymize individual names in combined reports:

```bash
# Names → Developer-A3F2, Developer-B7E1, etc.
impactlens full --hide-individual-names

# Also hides leave_days and capacity
impactlens jira full --hide-individual-names

impactlens pr full --hide-individual-names
```

### Upload Control

```bash
# Upload ALL reports including members
impactlens full --upload-members

# Skip all uploads
impactlens jira full --no-upload

# Upload PR members reports
impactlens pr full --upload-members
```

### AI-Powered Insights

```bash
# With Claude insights (requires Claude Code CLI or ANTHROPIC_API_KEY)
impactlens full --with-claude-insights --claude-api-mode
```

See [AI-Powered Analysis](../README.md#ai-powered-analysis-experimental) for setup details.

### Incremental PR Fetching

```bash
# Fetch only new PRs (faster)
impactlens pr team --incremental

impactlens pr member testcara --incremental --no-upload
```

### Custom Config Files

All commands support `--config` to use custom configuration:

```bash
impactlens jira full --config config/team-a/jira_report_config.yaml

impactlens pr full --config config/team-a/pr_report_config.yaml --upload-members

impactlens pr team --config config/team-a/pr_report_config.yaml --no-upload

impactlens pr member alice --config config/my-team/pr_report_config.yaml
```

## Docker Usage

Prefix CLI commands with `docker-compose run impactlens`:

```bash
# Verify setup
docker-compose run impactlens verify

# Generate all reports
docker-compose run impactlens full

# Upload all including members
docker-compose run impactlens full --upload-members

# Skip all uploads
docker-compose run impactlens jira full --no-upload

# Incremental PR fetching
docker-compose run impactlens pr member testcara --incremental
```

## Workflow Details

The `full` command workflow: Get metrics → Generate reports → Upload reports

**Key options:**

- `--no-upload` - Skip all Google Sheets uploads
- `--upload-members` - Upload individual member reports (default: only team and combined reports)
- `--incremental` - Fetch only new PRs (cache enabled by default, PR reports only)
- `--rest-api` - Use REST API instead of GraphQL for Jira metrics (default: GraphQL, ~30% faster)

**Upload Behavior:**

- **Default**: Only team and combined reports are uploaded to Google Sheets
- **Member reports**: Not uploaded by default (to save quota), use `--upload-members` to enable

## Output Files

### Jira Reports

Located in `reports/jira/` or custom `output_dir`:

- `jira_report_general_*.txt` - Phase reports (detailed metrics)
- `jira_comparison_general_*.tsv` - Comparison table (phases side-by-side)
- `{project}_combined_jira_report_*.tsv` - Combined view (all members grouped by metric)

### PR Reports

Located in `reports/github/` or custom `output_dir`:

- `pr_report_general_*.txt` - Phase reports (detailed metrics)
- `pr_comparison_general_*.tsv` - Comparison table (phases side-by-side)
- `{project}_combined_pr_report_*.tsv` - Combined view (all members grouped by metric)

### Aggregated Reports

Located in custom `output_dir` from aggregation config (for multi-repo teams):

- `aggregated_jira_report_*.tsv` - Unified Jira metrics across all repositories
- `aggregated_pr_report_*.tsv` - Unified PR metrics across all repositories

**Notes:**

- `{project}` prefix is added when `jira_project_key` or `github_repo_name` is configured
- Aggregated reports are generated only when `aggregation_config.yaml` is present

### AI Analysis Reports

Generated by default (unless disabled with `no_ai_analysis: true` or `--no-ai-analysis`):

- **Prompt files** (always generated):
  - `analysis_prompt_*.txt` - Single report analysis prompts
  - `combined_analysis_prompt_*.txt` - Combined Jira+PR analysis prompts

- **Analysis files** (when Gemini API key is configured):
  - `gemini_analysis_jira_*.txt` - AI insights for Jira metrics
  - `gemini_analysis_pr_*.txt` - AI insights for PR metrics
  - `gemini_analysis_combined_*.txt` - Combined Jira+PR insights

See [AI-Powered Analysis](#ai-powered-analysis) section below for setup and usage details.

## AI-Powered Analysis

> **💡 OPTIONAL** - Get AI-powered insights from your metrics reports

ImpactLens can automatically analyze your reports to extract insights on trends, bottlenecks, and actionable recommendations. AI analysis is **enabled by default** and runs automatically when you generate reports.

### What You Get

- **Executive Summary** - Overall AI impact assessment
- **Key Trends** - 3-5 critical insights on metric changes
- **Bottlenecks & Risks** - Issues and patterns requiring attention
- **Actionable Recommendations** - Concrete steps with measurable goals
- **AI Tool Impact** - Productivity assessment and effectiveness analysis
- **Auto-upload** - Results to Google Sheets (optional with `--no-upload`)

### Configuration

AI analysis is **enabled by default**. To disable it:

**Option 1: Config file (Recommended for CI)**

Add to your `jira_report_config.yaml` or `pr_report_config.yaml`:

```yaml
no_ai_analysis: true
```

**Option 2: CLI flag (for local runs)**

```bash
impactlens full --no-ai-analysis
```

### Usage Options

#### Option 1: Automatic Analysis with Gemini API (Default)

**Best for:** Automated workflows, CI/CD integration, local development

AI analysis runs automatically when you generate reports if `GOOGLE_API_KEY` is configured.

**Setup:**

```bash
# 1. Get API key from https://aistudio.google.com/apikey
# 2. Add to .env file
echo "GOOGLE_API_KEY=your-gemini-api-key" >> .env

# 3. For CLI: reload environment
source .env

# 4. For Docker: auto-loaded from .env
```

**Usage:**

```bash
# Generate reports with automatic AI analysis
impactlens full --config config/your-team

# Disable AI analysis if needed
impactlens full --config config/your-team --no-ai-analysis
```

**Generated Files:**

- **Prompt files** (always generated):
  - `analysis_prompt_*.txt` - Single report analysis prompts (Jira or PR)
  - `combined_analysis_prompt_*.txt` - Combined Jira+PR analysis prompts

- **Analysis files** (when Gemini API key is configured):
  - `gemini_analysis_jira_*.txt` - AI insights for Jira metrics
  - `gemini_analysis_pr_*.txt` - AI insights for PR metrics
  - `gemini_analysis_combined_*.txt` - Combined Jira+PR insights

All analysis files are automatically uploaded to Google Sheets (if configured).

**Pros:** Fully automated, works in CI/CD, supports both simple and aggregated reports
**Cons:** Requires API key, API costs (free tier: 1500 requests/day)

#### Option 2: Manual Analysis with Generated Prompts

**Best for:** Quick analysis, trying different AI models, no API key needed

If you don't have a Gemini API key, ImpactLens still generates ready-to-use prompts that you can use with any AI platform.

**Steps:**

1. Generate reports (locally or via CI):
   ```bash
   impactlens full --config config/your-team
   ```

2. Find generated prompt files in `reports/` folder:
   - `analysis_prompt_*.txt` - Single report analysis
   - `combined_analysis_prompt_*.txt` - Combined Jira+PR analysis

   **For CI users:** Download from PR workflow artifacts

3. Copy prompt content and paste into any AI platform:
   - **Claude** (https://claude.ai) - Recommended for best results
   - **ChatGPT** (https://chat.openai.com)
   - **Gemini** (https://gemini.google.com)

4. Get instant insights - the AI will analyze your metrics and provide:
   - Executive summary
   - Key trends and changes
   - Bottlenecks and risks
   - Actionable recommendations

**What's in the prompt file:**
- Your complete metrics report data (TSV format)
- Pre-configured analysis instructions
- Structured output format
- Phase comparison guidance
- Source report tracking

**Pros:** No API key needed, works with any AI, instant results, prompts already optimized
**Cons:** Manual copy-paste, one-time analysis

### Customization

Edit prompt templates to customize analysis:

- **Single report analysis**: `config/analysis_prompt_template.yaml`
- **Combined Jira+PR analysis**: `config/combined_analysis_prompt_template.yaml`

Customize:
- Analysis sections and focus areas
- Output format and structure
- Specific questions or metrics to emphasize

## Troubleshooting

### Common Issues

**1. Authentication errors:**

```bash
# Verify credentials are set
impactlens verify

# Check .env file
cat .env | grep -E "JIRA_TOKEN|GITHUB_TOKEN"
```

**2. Google Sheets upload fails:**

- Verify `GOOGLE_CREDENTIALS_FILE` and `GOOGLE_SPREADSHEET_ID` are set
- Ensure service account has Editor permission on spreadsheet
- See [Configuration Guide](CONFIGURATION.md#google-sheets-setup)

**3. Virtual environment issues:**

```bash
# Recreate virtual environment
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -e .
```

**4. Docker issues:**

```bash
# Rebuild container
docker-compose build --no-cache

# Check logs
docker-compose logs impactlens
```

### Getting Help

- **Issues**: https://github.com/testcara/impactlens/issues
- **Configuration Guide**: [docs/CONFIGURATION.md](CONFIGURATION.md)
- **Metrics Guide**: [docs/METRICS_GUIDE.md](METRICS_GUIDE.md)
- **Command help**: `impactlens --help`

## Next Steps

- **Configure Reports**: See [Configuration Guide](CONFIGURATION.md)
- **Understand Metrics**: See [Metrics Guide](METRICS_GUIDE.md)
- **CI/CD Setup**: See [GitHub Actions workflow](../README.md#-github-actions-ci-recommended---zero-config)
