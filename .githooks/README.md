# Git Hooks

This directory contains custom git hooks managed by pre-commit.

## Setup

After cloning the repository, install the pre-commit hooks:

```bash
pip install -e ".[dev]"  # Install dev dependencies including pre-commit
pre-commit install --hook-type commit-msg --hook-type pre-commit
```

## Available Hooks

### Pre-commit Hooks

- **Standard checks**: trailing whitespace, end-of-file-fixer, yaml validation, etc.
- **Tox lint**: Runs `tox -e lint` which includes black formatting and flake8 linting

### Commit-msg Hooks

- **AI Assistance Tracking**: Automatically adds "Assisted-by" trailers to commit messages for authorized users when Claude or Cursor is detected

## AI Assistance Tracking

The `commit-msg-ai-trailer.sh` hook automatically detects if you're using AI tools (Claude Code or Cursor) and adds an appropriate trailer to your commit message.

**Authorization**: Only users listed in `AI_authorized_emails.txt` will have AI trailers added.

**Detection**: The hook detects AI usage by:
1. Checking for running Claude/Cursor processes in the repository directory
2. Checking commit message content for AI-related markers

**Trailers added**:
- `Assisted-by: Claude` - When using Claude Code
- `Assisted-by: Cursor` - When using Cursor
- `Assisted-by: Cursor, Claude` - When using both

## Manual Testing

Test pre-commit hooks manually:

```bash
# Run all pre-commit hooks
pre-commit run --all-files

# Run specific hook
pre-commit run tox-lint --all-files
```

## Skipping Hooks

If you need to skip hooks temporarily (not recommended):

```bash
git commit --no-verify -m "commit message"
```
