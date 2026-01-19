# Configuration Guide

This guide explains how to configure ImpactLens for GitHub Actions CI-driven report generation.

## Table of Contents

- [Overview](#overview)
- [Two Configuration Scenarios](#two-configuration-scenarios)
  - [Scenario 1: Simple Team](#scenario-1-simple-team-single-projectrepo)
  - [Scenario 2: Complex Team](#scenario-2-complex-team-multi-projectrepo)
- [Configuration Reference](#configuration-reference)
- [Understanding Report Types](#understanding-report-types)
- [Privacy & Anonymization](#privacy--anonymization)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Overview

**Primary Usage Model:** Submit config via PR → CI auto-generates reports → View in PR comments or download artifacts

ImpactLens supports two configuration scenarios based on your team's complexity:

| Scenario    | Team Structure          | Configuration                                    | Reports Generated            |
| ----------- | ----------------------- | ------------------------------------------------ | ---------------------------- |
| **Simple**  | Single project/repo     | One config directory                             | TEAM + COMBINED              |
| **Complex** | Multiple projects/repos | Multiple config directories + aggregation config | TEAM + COMBINED + AGGREGATED |

---

## Two Configuration Scenarios

### Scenario 1: Simple Team (Single Project/Repo)

**Use when:** Your team works on a single Jira project and/or single GitHub/GitLab repository.

**Directory Structure:**

```
config/my-team/
├── jira_report_config.yaml
└── pr_report_config.yaml
```

**Configuration Example:**

See [Configuration Reference](#configuration-reference) for all available options. Key settings:

- **project**: Jira project key or GitHub/GitLab repo (owner/name format)
- **github_host** / **gitlab_host**: Optional, defaults to github.com or gitlab.com (for enterprise instances)
- **phases**: Analysis periods (e.g., before/after AI adoption)
- **team_members**: Team scope with optional leave_days and capacity
- **output_dir**: Where to save reports (e.g., `reports/my-team/jira`)

**Submit via PR:**

```bash
git clone https://github.com/testcara/impactlens.git
cd impactlens
mkdir -p config/my-team
# Copy and edit config files
git checkout -b my-team
git add -f config/my-team/
git commit -m "chore: generate AI impact report for my-team"
git push origin my-team
# Create PR → CI auto-generates reports
```

**Reports Generated:**

1. **Team Report** - Aggregated team metrics
2. **Combined Report** - Team + individual member breakdown (anonymized in CI)

Reports are posted as PR comments, uploaded to Google Sheets (anonymized), and available as workflow artifacts.

---

### Scenario 2: Complex Team (Multi-Project/Repo)

**Use when:**

- Team members work across multiple Jira projects (e.g., "KONFLUX" + "RHTAP")
- Team maintains multiple GitHub/GitLab repos (e.g., frontend + backend)
- You need unified team-wide metrics across all projects/repos

**Why 3 report types:**

- **TEAM reports** - Per-project/repo team performance (isolated view)
- **COMBINED reports** - Per-project/repo with member breakdown (detailed view)
- **AGGREGATED reports** - Unified cross-project/repo metrics (executive view)

**Directory Structure:**

```
config/platform-team/
├── aggregation_config.yaml       # Defines how to aggregate
├── frontend/                     # Sub-project 1
│   ├── jira_report_config.yaml
│   └── pr_report_config.yaml
├── backend/                      # Sub-project 2
│   ├── jira_report_config.yaml
│   └── pr_report_config.yaml
└── mobile/                       # Sub-project 3
    └── pr_report_config.yaml
```

**Sub-Project Configs:**

Each sub-project uses standard config (same as Scenario 1). **Critical requirements for aggregation:**

1. **Use same email across projects** for proper member aggregation
2. **Specify `output_dir` in ALL sub-project configs** with format: `reports/{project-name}/{source}`

⚠️ **Important:** The `{project-name}` must match the subdirectory name used in aggregation config.

**Example:**

```yaml
# frontend/pr_report_config.yaml
project: myorg/frontend-app
output_dir: reports/frontend/github  # Must specify for aggregation!
members:
  - email: charlie@company.com
    github_username: charlie-gh
    capacity: 0.5

# frontend/jira_report_config.yaml
project: FRONTEND
output_dir: reports/frontend/jira  # Must specify for aggregation!
members:
  - email: charlie@company.com  # Same email → will be aggregated
    capacity: 0.5

# backend/pr_report_config.yaml
project: myorg/backend-service
output_dir: reports/backend/github  # Must specify for aggregation!
members:
  - email: charlie@company.com  # Same email across all projects
    github_username: charlie-gh
    capacity: 0.5
```

**Why `output_dir` is required:** Aggregation looks for combined reports at `reports/{project-name}/*/combined_*.tsv`. Without explicit `output_dir`, reports may be saved to unexpected locations and aggregation will fail to find them.

**Aggregation Config:**

`config/platform-team/aggregation_config.yaml`:

```yaml
aggregation:
  name: "Platform Team"
  output_dir: "reports/platform-team-aggregated"

  # Sub-project directories to aggregate (must match directory names)
  projects:
    - "frontend"
    - "backend"
    - "mobile"

  # Optional: exclude specific combinations
  exclude:
    # - "mobile/jira"  # Skip if mobile has no Jira reports
```

**Submit via PR:**

```bash
mkdir -p config/platform-team/{frontend,backend,mobile}
# Edit config files for each sub-project and aggregation_config.yaml
git checkout -b report/platform-team
git add -f config/platform-team/
git commit -m "chore: generate AI impact report for platform-team"
git push origin report/platform-team
# Create PR → CI detects aggregation mode → auto-generates all reports
```

**Reports Generated:**

**Per Sub-Project:**

1. **Team Report** - Team metrics for frontend, backend, mobile (isolated)
2. **Combined Report** - Team + members for each sub-project (detailed)

**Aggregated:**

3. **Aggregated Report** - Unified team-wide metrics
   - **OVERALL column**: Total team performance across all projects
   - **Per-source columns**: frontend, backend, mobile
   - **Per-member columns**: alice, bob, charlie (auto-merged via email)

**Why All Three Report Types Are Necessary:**

Different sub-projects/repos often have **completely different characteristics**:

- **Frontend** may have shorter PRs, faster review cycles, higher AI adoption
- **Backend** may have complex PRs, longer testing cycles, lower AI adoption
- **Mobile** may have platform-specific workflows, different metrics patterns

**If you only see aggregated reports**, you would:
- ❌ **Miss critical sub-project insights** - Backend bottlenecks hidden by frontend speed
- ❌ **Get misleading averages** - High AI adoption in frontend masks low adoption in backend
- ❌ **Lose actionable context** - Can't identify which team/project needs improvement

**Each report type serves a purpose:**
- **Per Sub-Project Reports** → Identify specific bottlenecks and patterns in each project/repo
- **Aggregated Report** → Overall team performance and cross-project member contributions
- **Combined View** → Both perspectives needed for accurate analysis and decision-making

**Aggregation Logic:**

- **Sum metrics** (Total PRs, Total Issues): Values summed across projects
- **Average metrics** (Avg Time to Merge, AI Adoption Rate): Weighted average
- **Member deduplication**: Same `email` in multiple projects → single aggregated column

---

## Configuration Reference

### Project Settings

**Jira:**

```yaml
project:
  jira_url: "https://issues.redhat.com"
  jira_project_key: "Your Project Name"
```

**PR:**

```yaml
project:
  github_url: "https://github.com"  # Optional: defaults to https://github.com
  github_repo_owner: "your-org"
  github_repo_name: "your-repo"
```

### Phases

Define analysis periods for comparison:

```yaml
phases:
  - name: "Before AI"
    start: "2024-01-01"
    end: "2024-06-30"
  - name: "With AI"
    start: "2024-07-01"
    end: "2024-12-31"
```

**Notes:**

- Add as many phases as needed
- Use descriptive names (e.g., "No AI", "Cursor Only", "Claude + Cursor")
- Dates must be in `YYYY-MM-DD` format
- **All sub-projects must use identical phase definitions** for aggregation

### Team Members

**Jira:**

```yaml
members:
  - email: alice@company.com
    leave_days: 10 # Optional: days on leave
    capacity: 1.0 # Optional: 1.0 = full time
  - email: bob@company.com
    leave_days: [5, 8] # Optional: per-phase values
    capacity: [1.0, 0.5] # Optional: left team in phase 2
```

**PR:**

```yaml
members:
  - email: alice@company.com # Same email as Jira for consistent anonymization
    github_username: alice-github # GitHub username
  - email: bob@company.com
    github_username: bob-github
```

**Leave Days & Capacity:**

- **Leave Days**: Days on leave during the phase

  - Single value: `leave_days: 10` (applies to all phases)
  - Per-phase: `leave_days: [26, 20, 11.5]`

- **Capacity**: Work capacity (0.0 to 1.0)
  - `1.0` = Full time (100%)
  - `0.8` = 80% time (e.g., 4 days/week)
  - `0.5` = Half time
  - `0.0` = Not on team (member left)

Reports include **4 Daily Throughput metrics** for comprehensive analysis:

1. Skip leave days: `Total Issues / (Period - Leave Days)`
2. Based on capacity: `Total Issues / (Period × Capacity)`
3. Leave + capacity: `Total Issues / ((Period - Leave Days) × Capacity)`
4. Baseline: `Total Issues / Period`

### Output Directory

```yaml
# Simple scenario
output_dir: "reports/my-team/jira"

# Complex scenario - per sub-project
output_dir: "reports/frontend/jira"
output_dir: "reports/backend/jira"

# Aggregated - in aggregation_config.yaml
output_dir: "reports/platform-team-aggregated"
```

### AI Analysis (Optional)

Control whether AI-powered analysis is generated for your reports:

```yaml
# Disable AI analysis (enabled by default)
no_ai_analysis: true
```

**Default behavior:** AI analysis is **enabled** and runs automatically when you generate reports.

**When to disable:**
- You don't have a Gemini API key
- You prefer to use generated prompts manually with different AI platforms
- You want to reduce API costs or processing time

**What gets generated:**

With AI analysis **enabled** (default):
- Prompt files: `analysis_prompt_*.txt`, `combined_analysis_prompt_*.txt`
- Analysis files: `gemini_analysis_*.txt` (if `GOOGLE_API_KEY` is configured)
- Auto-upload to Google Sheets

With AI analysis **disabled** (`no_ai_analysis: true`):
- No prompts generated
- No analysis files generated
- Faster report generation

**See also:** [AI-Powered Analysis](LOCAL_DEVELOPMENT.md#ai-powered-analysis) for detailed setup and usage.

---

## Understanding Report Types

> **💡 Why multiple report types?** Each provides a necessary perspective - see [Why All Three Are Necessary](#why-all-three-report-types-are-necessary) above.

### 1. TEAM Report (`*_report_general_*.txt`)

**Purpose:** High-level team performance per phase

**Contains:** Total PRs/Issues, average time to merge/close, AI adoption rate, state distribution, team throughput

**Use for:** Quick team health check, phase-over-phase comparison

### 2. COMBINED Report (`combined_*_report_*.tsv`)

**Purpose:** Detailed breakdown with individual member columns

**Contains:**

- TEAM column (aggregated team metrics)
- Individual member columns (alice, bob, charlie, etc.)
- All metrics for each member
- Phase-over-phase comparison

**Use for:** Individual performance analysis, capacity planning, detailed reviews

**CI behavior:** Individual names automatically anonymized (`Developer-A3F2`, etc.)

### 3. AGGREGATED Report (`aggregated_*_report_*.tsv`)

**Only in Complex Scenario**

**Purpose:** Unified view across multiple projects/repos

**Contains:**

- OVERALL column (total team across all projects)
- Per-source columns (frontend, backend, mobile)
- Per-member columns (auto-merged across projects)

**Use for:** Executive reporting, team-wide AI impact, cross-project insights

**Example:**

```
Metric               | OVERALL | frontend | backend | alice  | bob    | charlie
---------------------|---------|----------|---------|--------|--------|--------
Total PRs            | 150     | 80       | 70      | 90     | 40     | 20
AI Adoption Rate (%) | 65%     | 70%      | 60%     | 80%    | 50%    | 60%
Avg Time to Merge    | 2.5d    | 2.3d     | 2.7d    | 2.1d   | 3.0d   | 2.5d
```

---

## Privacy & Anonymization

### Email Notifications (Optional)

When enabled, team members receive email notifications informing them of their **permanent anonymous identifier** (e.g., `Developer-A3F2`) when reports are generated. This allows members to find their personal metrics in anonymized reports while maintaining privacy control.

**Important**: Your anonymous ID is **permanent and consistent** across all reports. Once you receive it, you only need the email once. After that, you can disable email notifications to avoid repeated emails.

**Enable in Config:**

```yaml
# jira_report_config.yaml or pr_report_config.yaml
email_anonymous_id:
  enabled: true  # Set to false to disable email notifications
```

**To Disable After Receiving Your ID:**

```yaml
email_anonymous_id:
  enabled: false  # Disable future email notifications
```

**SMTP Configuration (required in .env for sending emails):**

```bash
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password  # Gmail App Password (not regular password)
```

**Gmail App Password Setup:**
1. Go to Google Account → Security → 2-Step Verification
2. Scroll to "App passwords" → Generate new app password
3. Select "Mail" and your device → Copy the 16-character password
4. Add to `.env` as `SMTP_PASSWORD`

**Command Line Options:**

- `--email-anonymous-id`: Enable email notifications for this run
- `--mail-save-file <directory>`: Save emails as HTML files instead of sending (useful for testing)

**Workflow Examples:**

**Single-team mode:**
```bash
# Send actual emails
impactlens full --hide-individual-names --email-anonymous-id

# Test mode: save emails as files without sending
impactlens full --hide-individual-names --email-anonymous-id \
  --mail-save-file reports/test-emails
```

**Multi-team mode:** Email notifications handled separately after aggregation to avoid duplicates
```bash
# Generate reports (no email flag to avoid duplicates)
impactlens jira full --hide-individual-names
impactlens pr full --hide-individual-names

# Aggregate
impactlens aggregate --config aggregation_config.yaml

# Send emails once (deduplicated automatically by email address)
python -m impactlens.scripts.send_email_notifications \
  --config-dir config/my-team

# Or test mode: save to files
python -m impactlens.scripts.send_email_notifications \
  --config-dir config/my-team \
  --mail-save-file reports/test-emails
```

**Why the difference?** In multi-team scenarios, members may appear in multiple sub-projects. The standalone script automatically deduplicates by email address to ensure each person receives only one notification.

### CI Auto-Anonymization

**What's anonymized:**

- Individual names → `Developer-A3F2`, `Developer-B7E1`, etc.
- Email addresses, leave days, capacity → Hidden

**What's NOT anonymized:**

- Team aggregated metrics
- Phase names, project/repo names

**Consistent hashing across Jira and PR:**

Add `email` field to PR config using the **same email** as Jira:

```yaml
# Jira config
team_members:
  - member: alice
    email: alice@company.com

# PR config
team_members:
  - name: alice-github
    email: alice@company.com  # Same email → same hash ✅
```

**Result:**

- Without email: Different hashes in Jira vs PR
- With email: Same hash in both (`Developer-1AC5`) ✅

### Local Full Data Access

To see non-anonymized data, run locally:

```bash
# Docker
cp .env.example .env && vim .env
docker-compose run impactlens full

# CLI
python3 -m venv venv && source venv/bin/activate
pip install -e . && source .env
impactlens full
```

---

## Best Practices

### ✅ Configuration

1. **Use consistent phases** across all sub-projects
2. **Add email field** to PR configs for consistent anonymization
3. **Match directory names** between `aggregation_config.yaml` and actual `config/` structure
4. **Use descriptive names** for sub-projects (e.g., `ui-frontend`, `api-backend`)

### ✅ Team Members

1. **Same email across projects** for proper aggregation
2. **Set realistic capacity** for part-time contributors
3. **Track leave days** for accurate throughput metrics
4. **Keep team lists updated** when members join/leave

### ✅ Git Workflow

1. **One PR per reporting period** (e.g., `report/team-2024-12`)
2. **Use `git add -f config/`** since config/ might be in `.gitignore`
3. **Wait for CI completion** before merging (reports in comments)
4. **Archive old report branches** after reviewing

### ✅ Multi-Project Teams

1. **Test individual configs first** before aggregation
2. **Use same phase definitions** across all sub-projects
3. **Verify output_dir** matches aggregation expectations
4. **Check member email consistency** across projects

---

## Troubleshooting

### CI not generating reports

**Check:**

1. Config files exist at correct paths (`config/{team}/`)
2. YAML syntax is valid (use YAML linter)
3. GitHub Actions workflow ran successfully
4. Repository secrets are configured

### Aggregation not working

**Common issues:**

- `projects` list doesn't match actual directory names
- Sub-project `output_dir` doesn't follow pattern `reports/{project}/jira`
- Phase definitions differ across sub-projects
- Combined reports don't exist yet (run individual reports first)

**Fix:**

```bash
# Verify directory structure
ls -la config/platform-team/
ls -la reports/frontend/jira/

# Check aggregation config matches directories
cat config/platform-team/aggregation_config.yaml
```

### Reports in wrong directory

**Check:**

- `output_dir` in config file
- Path uses forward slashes (`reports/team/jira` not `reports\team\jira`)
- Directory is writable

### Member appears multiple times in aggregated report

**This is expected** if they work on multiple projects. Verify:

- Same `email` used across all project configs → Merged correctly ✅
- Different `email` or missing → Treated as separate people ❌

### No team members found

**Check:**

- Config file exists (not just `.example` template)
- YAML syntax is correct (proper indentation)
- `members` section is not empty
- Email addresses are correctly configured
- GitHub usernames match actual GitHub accounts (for PR configs)

---

## Next Steps

- **[METRICS_GUIDE.md](METRICS_GUIDE.md)** - Metric explanations and formulas
- **[README.md](../README.md)** - Quick Start and Usage Examples
- **Report issues:** https://github.com/testcara/impactlens/issues
