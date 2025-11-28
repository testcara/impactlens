# Contributing Guide

Thank you for your interest in contributing to AI Impact Analysis! This guide will help you set up your development environment, write code, run tests, and submit changes.

## Table of Contents

- [Development Setup](#development-setup)
- [Code Contribution Workflow](#code-contribution-workflow)
- [Commit Guidelines](#commit-guidelines)
- [Testing](#testing)
- [Code Quality](#code-quality)
- [Documentation](#documentation)
- [Getting Help](#getting-help)

## Development Setup

### 1. Fork and Clone

```bash
# Fork the repository on GitHub, then clone your fork
git clone https://github.com/YOUR_USERNAME/ai_impact_analysis.git
cd ai_impact_analysis
```

### 2. Set Up Environment

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install package in editable mode with dev dependencies
pip install -e ".[dev]"
```

### 3. Configure Environment Variables

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
ai-impact-analysis --help
```

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

### Manual Testing Workflow

**Test CLI commands:**

```bash
# Verify setup
ai-impact-analysis verify

# Test Jira workflow
ai-impact-analysis jira team

# Test PR workflow
ai-impact-analysis pr team

# Test full workflow
ai-impact-analysis full
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
ai-impact-analysis jira team --config test-config.yaml
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

- **Questions**: Open a [Discussion](https://github.com/testcara/ai_impact_analysis/discussions)
- **Bug Reports**: Open an [Issue](https://github.com/testcara/ai_impact_analysis/issues)
- **Feature Requests**: Open an [Issue](https://github.com/testcara/ai_impact_analysis/issues) with `enhancement` label

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
from ai_impact_analysis.core.new_feature import calculate_metric

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
    from ai_impact_analysis.clients.jira_client import JiraClient

    client = JiraClient()
    issues = client.fetch_issues(start_date="2024-01-01", end_date="2024-01-31")

    assert len(issues) > 0
    assert "key" in issues[0]
```

## Thank You!

Your contributions make this project better for everyone. We appreciate your time and effort! 🎉
