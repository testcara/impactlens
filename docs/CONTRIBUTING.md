# Contributing Guide

Thank you for your interest in contributing to AI Impact Analysis! This guide will help you set up your development environment, write code, run tests, and submit changes.

## Table of Contents

- [Project Structure](#project-structure)
- [Development Setup](#development-setup)
- [Code Contribution Workflow](#code-contribution-workflow)
- [Commit Guidelines](#commit-guidelines)
- [Testing](#testing)
- [Code Quality](#code-quality)
- [Documentation](#documentation)
- [Getting Help](#getting-help)

## Project Structure

Understanding the project structure helps you navigate the codebase and know where to make changes.

```
impactlens/
├── impactlens/           # Core library
│   ├── cli.py                    # CLI entry point
│   ├── clients/                  # API clients
│   │   ├── jira_client.py        # Jira REST/GraphQL API
│   │   ├── github_client_graphql.py  # GitHub GraphQL
│   │   ├── github_client.py      # GitHub REST API (legacy)
│   │   └── sheets_client.py      # Google Sheets API
│   ├── core/                     # Business logic
│   │   ├── jira_metrics_calculator.py
│   │   ├── pr_metrics_calculator.py
│   │   ├── jira_report_generator.py
│   │   ├── pr_report_generator.py
│   │   ├── report_aggregator.py  # Multi-team aggregation
│   │   └── report_orchestrator.py
│   ├── models/                   # Data models & config
│   │   └── config.py             # Configuration models
│   ├── scripts/                  # Script modules
│   │   ├── generate_analysis_prompt.py  # Generate AI analysis prompts
│   │   ├── analyze_with_gemini.py       # Gemini API analysis
│   │   ├── get_jira_metrics.py
│   │   ├── get_pr_metrics.py
│   │   ├── generate_jira_report.py
│   │   ├── generate_pr_report.py
│   │   ├── generate_jira_comparison_report.py
│   │   ├── generate_pr_comparison_report.py
│   │   ├── aggregate_reports.py  # Multi-team report aggregation
│   │   ├── generate_charts.py    # Chart generation CLI
│   │   ├── send_email_notifications.py
│   │   ├── upload_to_sheets.py
│   │   ├── clear_google_sheets.py  # Utility to clean up old sheets
│   │   └── verify_setup.py
│   └── utils/                    # Shared utilities
│       ├── anonymization.py      # Privacy & anonymization utilities
│       ├── cli_utils.py          # CLI helper functions
│       ├── common_args.py        # Shared CLI argument definitions
│       ├── core_utils.py         # Core utility functions
│       ├── email_notifier.py     # Email notification utilities
│       ├── github_charts_uploader.py  # Upload charts to GitHub repo
│       ├── logger.py             # Logging configuration
│       ├── pr_utils.py           # PR-specific utilities
│       ├── report_preprocessor.py # Report data preprocessing
│       ├── report_utils.py       # Report generation utilities
│       ├── sheets_visualization.py # Google Sheets chart embedding
│       ├── smtp_config.py        # SMTP configuration & email helpers
│       ├── visualization.py      # Box plot chart generation
│       └── workflow_utils.py     # Config loading & workflow helpers
├── .github/workflows/            # GitHub Actions CI
│   ├── ci.yml                    # Test & lint workflow
│   ├── config-validation.yml     # Config-only PR validation
│   ├── gemini-analysis.yml       # AI analysis workflow
│   └── generate-reports.yml      # Automated report generation
├── config/                       # Configuration files
│   ├── jira_report_config.yaml.example  # Jira config template
│   ├── pr_report_config.yaml.example    # PR config template
│   ├── aggregation_config.yaml.example  # Multi-repo aggregation config
│   ├── analysis_prompt_template.yaml    # Single report AI analysis template
│   ├── combined_analysis_prompt_template.yaml  # Combined Jira+PR analysis template
│   ├── test-simple-team/         # CI basic test configs
│   │   ├── jira_report_config.yaml
│   │   └── pr_report_config.yaml
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
│   ├── LOCAL_DEVELOPMENT.md      # Local development guide
│   ├── METRICS_GUIDE.md          # Metrics explanations & formulas
│   └── CONTRIBUTING.md           # Contribution guidelines
├── tests/                        # Test suite
│   ├── test_jira_client.py
│   ├── test_github_client.py
│   ├── test_jira_integration.py
│   ├── test_github_integration.py
│   └── test_utils.py
├── .env.example                  # Environment variables template
├── requirements.txt              # Python dependencies
├── docker-compose.yml            # Docker Compose setup
├── Dockerfile                    # Docker build configuration
├── pyproject.toml                # Project metadata & CLI config
└── tox.ini                       # Test configuration
```

**Key directories for contributors:**

- `impactlens/core/` - Add new metrics calculators or report generators here
- `impactlens/clients/` - API client implementations (Jira, GitHub, GitLab, Google Sheets)
- `impactlens/utils/` - Shared utilities and helper functions
- `impactlens/scripts/` - Standalone scripts for specific tasks
- `tests/` - Unit and integration tests
- `docs/` - User and developer documentation
- `.github/workflows/` - CI/CD workflows

## Development Setup

### 1. Fork and Clone

```bash
# Fork the repository on GitHub, then clone your fork
git clone https://github.com/YOUR_USERNAME/impactlens.git
cd impactlens
```

### 2. Set Up Environment

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install package in editable mode with dev dependencies
pip install -e ".[dev]"
```

### 3. Configure Environment and Config Files

**Environment variables:**

```bash
# Copy example config
cp .env.example .env

# Edit .env with your API credentials
vim .env
```

Add your Jira and GitHub credentials to `.env` file. Required for testing:
- `JIRA_URL`, `JIRA_API_TOKEN`, `JIRA_PROJECT_KEY`
- `GITHUB_TOKEN`, `GITHUB_REPO_OWNER`, `GITHUB_REPO_NAME`

➡️ **See [Configuration Guide](CONFIGURATION.md#environment-variables) for complete environment variable reference.**

**Report configuration files:**

```bash
# Copy config templates
cp config/jira_report_config.yaml.example config/jira_report_config.yaml
cp config/pr_report_config.yaml.example config/pr_report_config.yaml

# Edit to customize team members, phases, and metrics
vim config/jira_report_config.yaml
vim config/pr_report_config.yaml
```

> **Note:** Config files (`.yaml`) are in `.gitignore` to keep your team-specific settings private. Only templates (`.example`) are committed to the repository.

### 4. Install Pre-commit Hooks (Recommended)

Pre-commit hooks automatically run linters and formatters before each commit:

```bash
# Install both commit-msg and pre-commit hooks
pre-commit install --hook-type commit-msg --hook-type pre-commit
```

**What the hooks do:**

- **Pre-commit hook**: Runs `black` (formatter) and `flake8` (linter) on staged files
- **Commit-msg hook**: Automatically adds "Assisted-by" trailers if you use AI tools (Claude, Cursor)

### 5. Verify Setup

```bash
# Run quick tests
tox -e unittest --develop

# Verify CLI is working
impactlens --help

# Test basic commands
impactlens verify
impactlens jira team
```

> **Note:** Docker images are automatically built from the `master` branch via Quay.io Build Triggers. You only need to test the CLI locally - once you push to master, the Docker image will be built automatically.

## Code Contribution Workflow

### 1. Create a Feature Branch

```bash
# Create and switch to a new branch
git checkout -b feature/your-feature-name

# Or for bug fixes
git checkout -b fix/issue-description
```

### 2. Make Your Changes

- Write clear, readable code
- Follow existing code style (enforced by `black` and `flake8`)
- Add docstrings to functions and classes
- Update tests if needed

### 3. Run Tests and Linters

```bash
# Run unit tests (fast, ~0.1s)
tox -e unittest --develop

# Run linters
tox -e lint

# Run type checking
tox -e type

# Auto-format code
tox -e format
```

### 4. Commit Your Changes

```bash
# Stage your changes
git add .

# Commit (pre-commit hooks will run automatically)
git commit -m "Add feature: brief description

Detailed explanation of what this commit does and why.

Fixes #123"
```

**Note:** If you used AI assistance, the commit-msg hook will automatically add:
```
Assisted-by: Claude <noreply@anthropic.com>
```

### 5. Push and Create Pull Request

```bash
# Push to your fork
git push origin feature/your-feature-name

# Go to GitHub and create a Pull Request
```

## Commit Guidelines

### Commit Message Format

```
<type>: <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `test`: Adding or updating tests
- `refactor`: Code refactoring
- `style`: Code style/formatting changes
- `chore`: Build process, dependencies, etc.

**Example:**

```bash
git commit -m "feat: add incremental PR fetching

Implement --incremental flag to fetch only new PRs since last run.
This improves performance by using cached data and reducing API calls.

- Add cache mechanism for PR metadata
- Update GitHub client to support incremental fetching
- Add tests for cache functionality

Fixes #42"
```

### AI-Assisted Commits

If you use AI coding assistants (Claude, Cursor, etc.), the commit-msg hook will automatically add trailers:

```
feat: implement new metric calculator

Added daily throughput metric with capacity adjustment.

Assisted-by: Claude <noreply@anthropic.com>
```

## Testing

### Test Types

#### Unit Tests (Fast, ~0.1s)

Test individual components in isolation using mocks:

```bash
# Run all unit tests
tox -e unittest --develop

# Run specific test file
pytest tests/test_utils.py -v

# Run with coverage report
tox -e coverage --develop
```

**Coverage:**
- `tests/test_utils.py` - Utility functions
- `tests/test_jira_client.py` - Jira API client
- `tests/test_github_client.py` - GitHub API client

#### Integration Tests (Slow, requires credentials)

Test real API calls end-to-end:

```bash
# Jira integration tests
tox -e jira-integration

# GitHub integration tests
tox -e github-integration
```

**Note:** Integration tests make real API calls and are slow. Run unit tests during development.

#### CI Integration Tests (Automated)

When you commit Python code changes, CI automatically runs integration tests using test configs:

```bash
# Test configs are in config/test/
# - jira_report_config.yaml: 2-week test period, 2 members
# - pr_report_config.yaml: 2-week test period, 2 members

# You can run the same tests locally:
python -m impactlens.cli jira full \
  --config config/test/jira_report_config.yaml \
  --no-upload

python -m impactlens.cli pr full \
  --config config/test/pr_report_config.yaml \
  --no-upload
```

**CI Workflow:**
1. **Trigger**: Python code changes (`.py`, `pyproject.toml`, `requirements.txt`)
2. **Steps**: Unit tests → Lint → Type check → **Integration test**
3. **Output**: Test reports uploaded as artifacts (7-day retention)

This validates the full pipeline executes correctly with real API calls.

### Manual Testing Workflow

**Test CLI commands:**

```bash
# Verify setup
impactlens verify

# Test Jira workflow
impactlens jira team

# Test PR workflow
impactlens pr team

# Test full workflow
impactlens full
```

**Test with custom config:**

```bash
# Create test config
cat > test-config.yaml <<EOF
phases:
  - name: "Test Phase"
    start: "2024-01-01"
    end: "2024-01-31"
EOF

# Run with custom config
impactlens jira team --config test-config.yaml
```

## Code Quality

### Linting

```bash
# Check code style
tox -e lint

# Auto-format code (fixes most issues)
tox -e format
```

We use:
- **black**: Code formatter (line length: 100)
- **flake8**: Style checker
- **isort**: Import sorting

### Type Checking

```bash
# Run mypy type checker
tox -e type
```

### Before Committing

Run this checklist:

```bash
# 1. Format code
tox -e format

# 2. Run linters
tox -e lint

# 3. Run type checking
tox -e type

# 4. Run unit tests
tox -e unittest --develop

# Or run all at once (slower)
tox
```

## Documentation

### Update Documentation

When adding features or changing behavior:

1. **README.md**: Update usage examples
2. **docs/CONFIGURATION.md**: Update configuration options
3. **docs/METRICS_GUIDE.md**: Document new metrics
4. **Docstrings**: Add/update docstrings in code

### Documentation Style

- Use clear, concise language
- Include code examples
- Use Markdown formatting
- Link to related sections

## Getting Help

- **Questions**: Open a [Discussion](https://github.com/testcara/impactlens/discussions)
- **Bug Reports**: Open an [Issue](https://github.com/testcara/impactlens/issues)
- **Feature Requests**: Open an [Issue](https://github.com/testcara/impactlens/issues) with `enhancement` label

## Pull Request Checklist

Before submitting a PR, ensure:

- [ ] Code follows project style (black, flake8)
- [ ] Tests pass (`tox -e unittest --develop`)
- [ ] Type checking passes (`tox -e type`)
- [ ] Documentation updated (if needed)
- [ ] Commit messages follow guidelines
- [ ] Branch is up to date with `master`
- [ ] PR description explains what and why

## Appendix: Testing Details

### Running Specific Tests

```bash
# Run specific test file
pytest tests/test_utils.py -v

# Run specific test function
pytest tests/test_utils.py::test_convert_to_date -v

# Run tests matching pattern
pytest -k "test_jira" -v
```

### Test Coverage

```bash
# Generate coverage report
tox -e coverage --develop

# View HTML coverage report
open htmlcov/index.html
```

### Adding New Tests

**Unit Test Example:**

```python
# tests/test_new_feature.py
import pytest
from impactlens.core.new_feature import calculate_metric

def test_calculate_metric():
    """Test metric calculation."""
    result = calculate_metric(data=[1, 2, 3])
    assert result == 2.0  # Expected average
```

**Integration Test Example:**

```python
# tests/test_jira_integration.py
import pytest
import os

@pytest.mark.skipif(
    not os.getenv("JIRA_API_TOKEN"),
    reason="JIRA_API_TOKEN not set"
)
def test_fetch_issues():
    """Test fetching real Jira issues."""
    from impactlens.clients.jira_client import JiraClient

    client = JiraClient()
    issues = client.fetch_issues(start_date="2024-01-01", end_date="2024-01-31")

    assert len(issues) > 0
    assert "key" in issues[0]
```

## Thank You!

Your contributions make this project better for everyone. We appreciate your time and effort! 🎉
