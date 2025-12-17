# ImpactLens CI Integration Test Reports

## Overview

This document explains the reports generated during CI integration tests. These reports are automatically generated on every push/PR to validate the full reporting pipeline.

## 📊 What Are These Reports?

The CI integration tests generate **real reports** using test configurations against actual repositories (impactlens itself and konflux-ui). These reports demonstrate:

- ✅ Full end-to-end pipeline functionality
- ✅ Report generation for Jira and GitHub PR metrics
- ✅ Multi-team aggregation capabilities
- ✅ Report format consistency and correctness

## 🗂️ Report Structure

The integration test generates reports in multiple directories:

```
reports/
├── test-ci-team/              # Scenario 1: Basic single-team reports
│   ├── jira/                  # Jira issue metrics
│   │   ├── jira_report_general_*.txt
│   │   ├── jira_comparison_general_*.tsv
│   │   └── combined_jira_report_*.tsv
│   └── github/                # GitHub PR metrics
│       ├── pr_report_general_*.txt
│       ├── pr_comparison_general_*.tsv
│       └── combined_pr_report_*.tsv
│
├── test-ci-team1/             # Scenario 2: Multi-team aggregation (Team 1)
│   ├── jira/
│   └── github/
│
├── test-ci-team2/             # Scenario 2: Multi-team aggregation (Team 2)
│   ├── jira/
│   └── github/
│
└── test-ci-aggregated/        # Scenario 2: Aggregated cross-team reports
    ├── aggregated_jira_report_*.tsv
    └── aggregated_pr_report_*.tsv
```

## 📋 Test Scenarios

### Scenario 1: Basic Integration Test (Single Team)

**Purpose**: Validates basic report generation for a single team

- **Config**: `config/test-integration-ci/test-ci-team/`
- **Test Data**:
  - Jira: KONFLUX project issues
  - GitHub: konflux-ci/konflux-ui repository PRs
- **Reports Generated**:
  - `reports/test-ci-team/jira/` - Jira metrics reports
  - `reports/test-ci-team/github/` - PR metrics reports

**What to Check**:
- ✅ All report files are generated
- ✅ Data format is correct (TSV columns aligned)
- ✅ No error messages in reports
- ✅ Individual names are anonymized (Developer-XXXX format)

---

### Scenario 2: Multi-Team Aggregation Test

**Purpose**: Validates multi-repository/team aggregation functionality

- **Config**:
  - Team 1: `config/test-aggregation-ci/test-ci-team1/`
  - Team 2: `config/test-aggregation-ci/test-ci-team2/`
  - Aggregation: `config/test-aggregation-ci/aggregation_config.yaml`

- **Test Data**: Same as Scenario 1, but split across two "teams"

- **Reports Generated**:
  - `reports/test-ci-team1/` - Team 1 individual reports
  - `reports/test-ci-team2/` - Team 2 individual reports
  - `reports/test-ci-aggregated/` - **Unified aggregated reports** 🔗

**What to Check**:
- ✅ Aggregated reports exist in `test-ci-aggregated/`
- ✅ Aggregated reports contain "OVERALL" column
- ✅ Project columns present (test-ci-team1, test-ci-team2)
- ✅ Aggregation note is displayed at the top
- ✅ Metrics are correctly summed (counts) or averaged (times)

## 🔍 How to Review Reports

### 1. Download Artifacts

In the GitHub Actions run page:
1. Scroll to the bottom → **Artifacts** section
2. Download `integration-test-reports.zip`
3. Extract and explore the directories

### 2. Verify Report Format

**Combined Reports** (`combined_*_report_*.tsv`):
```
=== Total Issues Closed ===
Phase           team    Developer-A3F2  Developer-B7E1  ...
Before AI       45      12              15              ...
With AI         78      23              28              ...
```

**Aggregated Reports** (`aggregated_*_report_*.tsv`):
```
Note: OVERALL column aggregates across all projects.
      For count/total metrics: sum across projects
      For average metrics: average across projects

=== Total Issues Closed ===
Phase        OVERALL  test-ci-team1  test-ci-team2  Developer-A3F2  ...
Before AI    90       45             45             12              ...
With AI      156      78             78             23              ...
```

### 3. Common Issues to Check

❌ **Reports are empty or missing**
- Check if test configs exist and are committed to git
- Verify API credentials in GitHub Secrets

❌ **Aggregation failed**
- Check if combined reports were generated first
- Verify `aggregation_config.yaml` project paths match actual report directories

❌ **Names not anonymized**
- Integration tests should always use `--hide-individual-names` flag
- Verify no real names appear in combined/aggregated reports

## 🔒 Privacy & Data

**Important Notes**:
- ✅ Individual names are **anonymized** as `Developer-XXXX` hashes
- ✅ Email addresses are **hidden** in CI reports
- ✅ `leave_days` and `capacity` fields are **removed**
- ⚠️ Project names and issue/PR titles are **visible** (test data is public)

These reports use **real data** from public repositories:
- **Jira**: Red Hat KONFLUX project (public issues)
- **GitHub**: konflux-ci/konflux-ui (public repository)

## 📝 Configuration Files Used

### Single Team Test
- `config/test-integration-ci/test-ci-team/jira_report_config.yaml`
- `config/test-integration-ci/test-ci-team/pr_report_config.yaml`

### Multi-Team Aggregation Test
- `config/test-aggregation-ci/test-ci-team1/jira_report_config.yaml`
- `config/test-aggregation-ci/test-ci-team1/pr_report_config.yaml`
- `config/test-aggregation-ci/test-ci-team2/jira_report_config.yaml`
- `config/test-aggregation-ci/test-ci-team2/pr_report_config.yaml`
- `config/test-aggregation-ci/aggregation_config.yaml`

## 🎯 Purpose of Integration Tests

These integration tests serve multiple purposes:

1. **Validation**: Ensure the full reporting pipeline works end-to-end
2. **Regression Testing**: Catch breaking changes before they reach production
3. **Documentation**: Provide real examples of report output formats
4. **Demo**: Show potential users what reports look like with real data

## 🔧 Troubleshooting

### Reports Not Generated

Check the workflow logs for error messages:

```bash
# In GitHub Actions → Integration Test job
Step 1: Jira reports
Step 2: PR reports
Step 3: Aggregation (if applicable)
```

Common errors:
- `Config file does not exist` → Config file not committed to git
- `API credentials not found` → GitHub Secrets not configured
- `No reports found for aggregation` → Combined reports weren't generated

### Aggregation Failed

Verify the aggregation config matches actual report paths:

```yaml
# config/test-aggregation-ci/aggregation_config.yaml
aggregation:
  projects:
    - test-ci-team1    # Must match reports/test-ci-team1/
    - test-ci-team2    # Must match reports/test-ci-team2/
```

## 📚 Related Documentation

- [Configuration Guide](CONFIGURATION.md) - How to set up your own configs
- [Metrics Guide](METRICS_GUIDE.md) - Understanding report metrics
- [README](../README.md#ai-powered-analysis-experimental) - Main project documentation

## ✅ Expected Outcomes

After a successful CI integration test run, you should see:

- ✅ All test jobs pass (Python 3.11, 3.12, 3.13)
- ✅ Integration test job completes successfully
- ✅ Artifacts available for download (`integration-test-reports.zip`)
- ✅ Reports contain data (not empty)
- ✅ Individual names anonymized in all reports
- ✅ Aggregated reports show "OVERALL" and project columns (Scenario 2)

---

**Last Updated**: December 2024
**Questions?** [Open an issue](https://github.com/testcara/impactlens/issues)
