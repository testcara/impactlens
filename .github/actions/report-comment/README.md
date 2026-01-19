# Report Statistics and PR Comment Action

A reusable composite action that collects report statistics and posts a detailed PR comment.

## Features

- ✅ Counts team reports, member reports, combined reports, and analysis prompts
- ✅ Automatically posts PR comment with detailed breakdown
- ✅ Supports custom report directories
- ✅ Works with both generate-reports and integration-test workflows

## Usage

```yaml
- name: Report Statistics and PR Comment
  uses: ./.github/actions/report-comment
  with:
    reports_dir: 'reports'  # or 'reports/test' for integration tests
    google_spreadsheet_id: ${{ secrets.GOOGLE_SPREADSHEET_ID }}
    github_token: ${{ secrets.GITHUB_TOKEN }}
```

## Inputs

| Name | Description | Required | Default |
|------|-------------|----------|---------|
| `reports_dir` | Directory containing reports | No | `reports` |
| `google_spreadsheet_id` | Google Spreadsheet ID for sharing link | No | `''` |
| `github_token` | GitHub token for PR comments | Yes | - |

## Outputs

| Name | Description |
|------|-------------|
| `json_count` | Number of JSON files |
| `team_comparison_count` | Number of team comparison reports |
| `member_comparison_count` | Number of member comparison reports |
| `combined_count` | Number of combined reports |
| `total_tsv` | Total TSV files |
| `prompt_count` | Number of analysis prompt files |
| `phase_report_count` | Number of detailed phase report files |
| `total_txt` | Total TXT files |

## Example PR Comment

```markdown
## ✅ Reports Generated Successfully

📊 **Report Summary**:
- **Total Reports**: 98 files (26 TSV + 72 TXT)
  - Team comparison: 2 TSV (Jira team + PR team)
  - Individual comparison: 22 TSV (11 Jira members + 11 PR members)
  - Combined views: 2 TSV (Jira combined + PR combined)
  - Detailed phase reports: 72 TXT (per-phase breakdowns for all members)
- **AI Analysis Prompts**: 2 files (Jira prompt + PR prompt)
- **Raw Metrics Data**: 72 JSON files (raw API responses)

📥 **Access Reports**: [View in Google Sheets] | [Download All Files]

> 💡 **Quick Tip**: Download prompt files from artifacts and paste into ChatGPT/Gemini for automated analysis!

---

⚠️ **Important**: ❌ DO NOT MERGE - 🔒 Manually close this PR after reviewing reports
```

## Used By

- `.github/workflows/generate-reports.yml` - Main report generation workflow
- `.github/workflows/ci.yml` - Integration test workflow
