# Manual Tests

This directory contains scripts for manually testing ImpactLens integrations with external services.

## 📋 Available Tests

### 1. JIRA API Test (`test_jira_api.py`)

Tests JIRA API v3 connectivity and query functionality.

**Setup:**
```bash
export JIRA_URL="https://redhat.atlassian.net"
export JIRA_EMAIL="your-email@redhat.com"
export JIRA_API_TOKEN="your-jira-token"
```

**Usage:**
```bash
python tests/manual/test_jira_api.py
```

**What it tests:**
- Simple JQL queries
- Assignee filtering (by email)
- Date format variations
- Complex queries with multiple conditions
- Token-based pagination

---

### 2. GitHub/GitLab Client Test (`test_github_gitlab_client.py`)

Tests GitHub and GitLab GraphQL API integration.

#### Testing GitHub

**Setup (Recommended - using new GIT_* variables):**
```bash
export GIT_URL="https://github.com"
export GITHUB_TOKEN="ghp_your_github_token"  # or GIT_TOKEN
export GIT_REPO_OWNER="redhat-appstudio"
export GIT_REPO_NAME="konflux-ui"
```

**Setup (Legacy - still supported):**
```bash
export GITHUB_URL="https://github.com"
export GITHUB_TOKEN="ghp_your_github_token"
export GITHUB_REPO_OWNER="redhat-appstudio"
export GITHUB_REPO_NAME="konflux-ui"
```

**Usage:**
```bash
python tests/manual/test_github_gitlab_client.py \
  --platform github \
  --start 2024-01-01 \
  --end 2024-01-31
```

**Optional filters:**
```bash
# Filter by author
python tests/manual/test_github_gitlab_client.py \
  --platform github \
  --start 2024-01-01 \
  --end 2024-01-31 \
  --author octocat

# Show more PRs
python tests/manual/test_github_gitlab_client.py \
  --platform github \
  --start 2024-01-01 \
  --end 2024-01-31 \
  --max-prs 10
```

#### Testing GitLab

**Setup (Recommended - using new GIT_* variables):**
```bash
export GIT_URL="https://gitlab.com"  # or your self-hosted instance
export GITLAB_TOKEN="glpat-your_gitlab_token"  # or GIT_TOKEN
export GIT_REPO_OWNER="gitlab-org"
export GIT_REPO_NAME="gitlab"
```

**Setup (Legacy - still supported):**
```bash
export GITHUB_URL="https://gitlab.com"
export GITHUB_TOKEN="glpat-your_gitlab_token"  # backward compatibility
export GITHUB_REPO_OWNER="gitlab-org"
export GITHUB_REPO_NAME="gitlab"
```

**Usage:**
```bash
python tests/manual/test_github_gitlab_client.py \
  --platform gitlab \
  --start 2024-01-01 \
  --end 2024-01-31
```

**Self-hosted GitLab:**
```bash
export GIT_URL="https://gitlab.your-company.com"
export GITLAB_TOKEN="glpat-your_token"  # or GIT_TOKEN
export GIT_REPO_OWNER="your-group"
export GIT_REPO_NAME="your-project"

python tests/manual/test_github_gitlab_client.py \
  --platform gitlab \
  --start 2024-01-01 \
  --end 2024-01-31
```

**Self-hosted GitLab with self-signed certificate:**
```bash
export GIT_URL="https://gitlab.your-company.com"
export GIT_VERIFY_SSL="false"  # Disable SSL verification for self-signed certs
export GITLAB_TOKEN="glpat-your_token"
export GIT_REPO_OWNER="your-group"
export GIT_REPO_NAME="your-project"

python tests/manual/test_github_gitlab_client.py \
  --platform gitlab \
  --start 2024-01-01 \
  --end 2024-01-31
```

> ⚠️ **Security Note**: Only disable SSL verification (`GIT_VERIFY_SSL=false`) for internal instances with self-signed certificates. Never use this with public services.

**What it tests:**
- Connection to GitHub/GitLab
- GraphQL query construction (platform-specific)
- Fetching merged PRs/MRs
- All expected metrics are present
- Caching functionality
- Performance comparison (cache vs no-cache)

---

## 🔑 Getting API Tokens

### GitHub Token

1. Go to https://github.com/settings/tokens
2. Generate new token (classic)
3. Select scopes: `repo` (full control)
4. Copy token and set as `GITHUB_TOKEN` (or `GIT_TOKEN` for unified config)

### GitLab Token

1. Go to https://gitlab.com/-/profile/personal_access_tokens (or your instance)
2. Create personal access token
3. Select scopes: `api`, `read_api`, `read_repository`
4. Copy token and set as `GITLAB_TOKEN` (or `GIT_TOKEN` for unified config)

### Multi-Platform Teams

If your team uses both GitHub and GitLab repositories:

**Recommended Setup:**
```bash
# For GitHub repos
export GIT_URL="https://github.com"
export GITHUB_TOKEN="ghp_your_github_token"
export GIT_REPO_OWNER="your-org"
export GIT_REPO_NAME="your-repo"

# For GitLab repos (in another shell or CI config)
export GIT_URL="https://gitlab.com"
export GITLAB_TOKEN="glpat_your_gitlab_token"
export GIT_REPO_OWNER="your-group"
export GIT_REPO_NAME="your-project"
```

**In GitHub Actions (to access both platforms):**
```yaml
env:
  GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}  # for GitHub repos
  GITLAB_TOKEN: ${{ secrets.GITLAB_TOKEN }}  # for GitLab repos
```

### JIRA Token

1. Go to https://id.atlassian.com/manage-profile/security/api-tokens
2. Create API token
3. Copy token and set as `JIRA_API_TOKEN`

---

## 📊 Test Output

Each test provides detailed output including:

- ✓/✗ Status for each test
- Sample data (PRs, MRs, Issues)
- GraphQL queries (for debugging)
- Performance metrics
- Error details (if any)

### Example Output

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  TEST 1: Connection Test
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✓ Connected to GitHub
  URL: https://api.github.com/graphql
  Repository: redhat-appstudio/konflux-ui
  Cache directory: .cache/github

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  TEST 3: Fetch PRs/MRs (2024-01-01 to 2024-01-31)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✓ Successfully fetched 15 PRs/MRs

📊 Sample PRs/MRs (showing first 5):
────────────────────────────────────────────────────────────────────────────────

1. PR #123: Fix authentication bug in login flow...
   Author: octocat
   Merged: 2024-01-15T10:30:00Z
   URL: https://github.com/org/repo/pull/123
   Changes: +50 -20 files:3
   AI Assistance: Yes (75.0% commits)
   Reviews: 2 approvals, 3 human reviewers
   Comments: 5 human comments
```

---

## 🐛 Troubleshooting

### Common Issues

**Issue: "Missing environment variables"**
- Make sure all required environment variables are set
- Check for typos in variable names

**Issue: "403 Forbidden"**
- GitHub: Check token has `repo` scope
- GitLab: Check token has `api`, `read_api`, `read_repository` scopes
- JIRA: Check you have correct email and API token

**Issue: "No PRs/MRs found"**
- Check date range covers period with merged PRs/MRs
- Verify repository has merged PRs/MRs
- Check author filter (if used)

**Issue: "GraphQL errors"**
- GitHub: Verify repository is public or token has access
- GitLab: Check fullPath format is correct (`owner/repo`)
- Check GraphQL query output in test results

---

## 💡 Tips

1. **Start with a short date range** (e.g., 1 month) to test faster
2. **Use `--max-prs 1`** for quick sanity checks
3. **Check the logs** - DEBUG level shows all API calls
4. **Test cache** by running the same query twice
5. **Compare platforms** by testing both GitHub and GitLab with same date range

---

## 📚 Related Documentation

- [GitHub GraphQL API](https://docs.github.com/en/graphql)
- [GitLab GraphQL API](https://docs.gitlab.com/ee/api/graphql/)
- [JIRA REST API v3](https://developer.atlassian.com/cloud/jira/platform/rest/v3/)
