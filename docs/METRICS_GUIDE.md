# Report Metrics Guide

This guide provides detailed explanations of all metrics in Jira and GitHub PR reports.

## Table of Contents

- [GitHub PR Metrics](#github-pr-metrics)
  - [Basic PR Metrics](#basic-pr-metrics)
  - [Review Metrics](#review-metrics)
  - [Code Size Metrics](#code-size-metrics)
  - [Understanding PR Metrics](#understanding-pr-metrics)
- [Jira Metrics](#jira-metrics)
  - [Understanding N/A Values](#understanding-na-values)
  - [Basic Metrics](#basic-metrics)
  - [State Time Metrics](#state-time-metrics)
  - [Re-entry Rate Metrics](#re-entry-rate-metrics)
  - [Issue Type Distribution](#issue-type-distribution)
  - [Interpreting Metrics](#interpreting-metrics)

---

## GitHub PR Metrics

GitHub PR reports analyze pull request activity and review efficiency. Below are detailed explanations of each metric.

### Basic PR Metrics

#### Total PRs Merged (excl. bot-authored)

- **What it is**: Count of all human-authored pull requests that were merged during the analysis period
- **How it's calculated**: Direct count from GitHub API query filtering by merged status, date range, and excluding bot authors (CodeRabbit, Dependabot, Renovate, GitHub Actions, red-hat-konflux)
- **Example**: 25 PRs merged (bot-authored PRs like dependency updates are excluded)
- **Why it matters**: Indicates overall human code delivery volume; focuses analysis on developer work rather than automated PRs

#### AI Adoption Rate

- **What it is**: Percentage of merged PRs that used AI coding assistants (Claude, Cursor)
- **How it's calculated**: `(AI-Assisted PRs / Total PRs) × 100%`
- **Detection method**: Analyzes Git commit messages for "Assisted-by: Claude" or "Assisted-by: Cursor" trailers
- **Example**: 40% means 40% of PRs included AI-generated code
- **Why it matters**: Tracks AI tool adoption across the team

#### AI-Assisted PRs / Non-AI PRs

- **What it is**: Count breakdown of PRs with vs without AI assistance
- **Example**: 10 AI-assisted, 15 non-AI
- **Why it matters**: Shows absolute numbers behind adoption rate

#### Claude PRs / Cursor PRs

- **What it is**: Count of PRs using each specific AI tool
- **Note**: PRs can use multiple tools (some commits with Claude, others with Cursor)
- **Why it matters**: Tracks which AI tools are most popular

#### Avg Time to Merge (days)

- **What it is**: Average time from PR creation to merge
- **How it's calculated**: `Sum(Merged Date - Created Date) / Total PRs`, in days
- **Example**: 3.5d means PRs take 3.5 days on average from opening to merge
- **Why it matters**: Primary delivery speed indicator; lower values mean faster deployment

#### Avg Time to First Review (hours)

- **What it is**: Average time from PR creation until first human review is submitted
- **How it's calculated**: `Sum(First Review Time - Created Time) / PRs with Reviews`, in hours
- **Example**: 2.5h means PRs get initial review within 2.5 hours
- **Why it matters**: Indicates team responsiveness; faster reviews reduce PR cycle time

### Review Metrics

#### Avg Changes Requested

- **What it is**: Average number of times reviewers request changes per PR
- **How it's calculated**: Count of "CHANGES_REQUESTED" review states divided by total PRs
- **Example**: 0.8 means most PRs pass with minimal change requests
- **Why it matters**: Code quality indicator; lower values suggest better initial quality

#### Avg Commits per PR

- **What it is**: Average number of commits in each PR
- **How it's calculated**: `Sum(Commit Count) / Total PRs`
- **Example**: 2.3 commits per PR
- **Why it matters**: Can indicate PR size and complexity; very high values may suggest scope creep

#### Avg Reviewers

- **What it is**: Average number of unique reviewers per PR (includes all users, including bots)
- **How it's calculated**: `Sum(Unique Reviewer Count) / Total PRs`
- **Example**: 3.2 reviewers per PR
- **Why it matters**: Indicates code review coverage

#### Avg Reviewers (excl. bots)

- **What it is**: Average number of human reviewers per PR (excludes bots like CodeRabbit, Dependabot)
- **Bots excluded**: coderabbit, dependabot, renovate, github-actions, red-hat-konflux
- **Example**: 2.1 human reviewers per PR
- **Why it matters**: Shows actual human engagement in code review

#### Avg Comments

- **What it is**: Average total comments per PR (includes inline code comments, discussion comments, and review submission comments)
- **Includes**: All users (humans + bots), all comment types (including simple approvals)
- **Example**: 15.5 comments per PR
- **Why it matters**: Indicates overall review activity level

#### Avg Comments (excl. bots & approvals)

- **What it is**: Average substantive human discussion per PR
- **Excludes**:
  - Bot comments (from CodeRabbit, Dependabot, etc.)
  - Simple approval comments (empty or "LGTM", "approved", "👍")
  - Comments mentioning `@coderabbit` (human interactions with the bot)
- **Includes**: Only meaningful human-to-human review discussion
- **Example**: 5.2 substantive comments per PR
- **Why it matters**: Shows quality of human code review engagement; helps distinguish between bot activity and real human discussion

### Code Size Metrics

#### Avg Lines Added / Deleted

- **What it is**: Average code change size (additions and deletions)
- **How it's calculated**: Sum of additions/deletions across all PRs divided by PR count
- **Example**: 125 lines added, 45 lines deleted
- **Why it matters**: Indicates PR size and scope

#### Avg Files Changed

- **What it is**: Average number of files modified per PR
- **Example**: 8.5 files per PR
- **Why it matters**: Another PR size indicator; high values may indicate refactoring or cross-cutting changes

### Understanding PR Metrics

**Bot vs Human Metrics:**

- Regular metrics include all activity (bots + humans)
- "(excl. bots)" metrics show only human engagement
- The difference reveals bot contribution (e.g., CodeRabbit's review impact)

**Comment Quality:**

- "Avg Comments" = All comments including bot reviews and simple "LGTM"
- "Avg Comments (excl. bots & approvals)" = Substantive human discussion only
- Large difference indicates heavy bot usage or many simple approvals

**Positive AI Impact Indicators:**

- ↓ Avg Time to Merge (faster delivery)
- ↓ Avg Time to First Review (quicker team response)
- ↓ Avg Changes Requested (better code quality on first attempt)
- ↑ AI Adoption Rate (increasing tool usage)
- Stable or ↑ Avg Reviewers (excl. bots) (maintained human oversight)

**Things to Watch:**

- If "Avg Comments" is much higher than "Avg Comments (excl. bots & approvals)" → heavy bot reliance
- If "Avg Reviewers (excl. bots)" decreases significantly → potential reduction in human oversight
- If Avg Time to Merge decreases but Avg Changes Requested increases → speed without quality improvement

---

## Jira Metrics

This section explains Jira issue metrics and how they're calculated.

### Understanding N/A Values

**N/A (Not Applicable)** appears in reports when data is unavailable or not applicable for a specific metric:

**When N/A appears:**

1. **State Time Metrics** (e.g., "Waiting State Avg Time: N/A")
   - **Meaning**: No issues entered this workflow state during the period
   - **Example**: If "Waiting State Avg Time" shows N/A, it means zero issues were blocked/waiting
   - **Interpretation**: Could be positive (smooth workflow, no blockers) or simply mean that state isn't used in your workflow

2. **Re-entry Rate Metrics** (e.g., "Waiting Re-entry Rate: N/A")
   - **Meaning**: No issues re-entered this state (rate would be 0.00x)
   - **Example**: If "Review Re-entry Rate" shows N/A, all reviews passed on first attempt
   - **Interpretation**: Generally positive - indicates no rework in that state

3. **Period Information** (e.g., "Analysis Period: N/A")
   - **Meaning**: Date information is missing or couldn't be calculated
   - **Rare occurrence**: Usually indicates data quality issues in Jira

4. **Throughput Metrics** (e.g., "Daily Throughput: N/A")
   - **Meaning**: Period days couldn't be calculated, so throughput can't be computed
   - **Depends on**: Valid date range being available

**Comparing N/A across phases:**

| Metric           | Phase 1 | Phase 2 | Phase 3 | Interpretation                                         |
| ---------------- | ------- | ------- | ------- | ------------------------------------------------------ |
| Waiting State    | 30.77d  | N/A     | N/A     | Workflow improved - no blocking issues in later phases |
| Review Re-entry  | 1.13x   | N/A     | N/A     | Code quality improved - reviews pass first time        |
| Waiting Re-entry | 1.24x   | 1.33x   | N/A     | Further improvement in Phase 3 - no blocked issues     |

**Best practices:**

- **Don't ignore N/A** - it often indicates positive workflow improvements
- **Compare across phases** - N/A appearing in later phases may show AI tool benefits
- **Context matters** - N/A for "Waiting" is good; N/A for core states like "In Progress" would be concerning

### Basic Metrics

#### Analysis Period

- **What it is**: The time range covered by the data, calculated from the earliest resolved issue to the latest resolved issue
- **How it's calculated**: `(Latest Resolved Date) - (Earliest Resolved Date)`
- **Example**: If issues were resolved between 2024-10-24 and 2025-05-30, the period is 218 days
- **Why it matters**: Provides context for comparing throughput across different phases

#### Total Issues Completed

- **What it is**: Count of all Jira issues that reached "Done" status during the analysis period
- **How it's calculated**: Direct count from Jira API query with `status = Done` and resolved date filters
- **Example**: 45 issues completed
- **Why it matters**: Indicates overall team productivity volume

#### Average Closure Time

- **What it is**: Average time from issue creation to resolution (moved to "Done" status)
- **How it's calculated**: `Sum(Resolution Date - Created Date) / Total Issues`
- **Example**: 12.5 days means on average issues take 12.5 days from creation to completion
- **Why it matters**: Primary indicator of development velocity; lower is generally better

#### Longest Closure Time

- **What it is**: Maximum time any single issue took from creation to resolution
- **How it's calculated**: `Max(Resolution Date - Created Date)` across all issues
- **Example**: 45.2 days
- **Why it matters**: Identifies outliers and potential bottlenecks; extremely long closure times may indicate blocked or complex issues

#### Leave Days

- **What it is**: Total leave days during the analysis period
- **Individual reports**: Member's leave days for this phase
- **Team reports**: Sum of all team members' leave days
- **Example**: 26 days (individual), 37.5 days (team total)
- **Why it matters**: Provides context for throughput calculations; helps explain productivity variations

#### Capacity

- **What it is**: Work capacity as percentage of full-time equivalent (FTE)
- **Individual reports**: Member's work capacity (0.0 to 1.0)
- **Team reports**: Sum of all members' capacity (total FTE)
- **Example**: 0.8 (80% time, individual), 4.5 (4.5 FTE total, team)
- **Why it matters**: Accounts for part-time work; capacity = 0.0 indicates member left team

#### Daily Throughput (4 variants)

The tool calculates four throughput metrics to provide comprehensive productivity analysis:

1. **Daily Throughput (skip leave days)**
   - **Formula**: `Total Issues / (Analysis Period - Leave Days)`
   - **Example**: 28 issues / (220 - 26) days = 0.14/d
   - **Use case**: Team throughput accounting for vacation time

2. **Daily Throughput (average per capacity)**
   - **Formula**: `Total Issues / (Analysis Period × Total Capacity)`
   - **Example**: 28 issues / (220 × 0.8) = 0.16 issues/capacity/day
   - **Use case**: Average productivity per capacity unit, comparable across different team sizes
   - **Note**: For teams, Total Capacity = sum of all members' capacity (e.g., 6-person team at full time = 6.0, or 5.5 if some members are part-time)

3. **Daily Throughput (average per capacity, excl. leave)**
   - **Formula**: `Total Issues / ((Analysis Period - Leave Days) × Total Capacity)`
   - **Example**: 28 issues / ((220 - 26) × 0.8) = 0.18 issues/capacity/day
   - **Use case**: Most accurate per-capacity metric - accounts for both vacation and capacity

4. **Daily Throughput**
   - **Formula**: `Total Issues / Analysis Period`
   - **Example**: 28 issues / 220 days = 0.13/d
   - **Use case**: Team baseline throughput for simple period-to-period comparison

### State Time Metrics

These metrics track how long issues spend in each workflow state. The calculation uses Jira's changelog to track every status transition.

**How State Times are Calculated:**

1. For each issue, we extract its complete status transition history from Jira changelog
2. We calculate time spent in each state by measuring time between transitions:
   - `State Duration = (Transition Out Time) - (Transition In Time)`
3. If an issue enters the same state multiple times (re-entry), all durations are summed
4. Average is calculated across all issues: `Avg State Time = Sum(All State Durations) / Number of Issues`

**Common States:**

#### New State Avg Time

- **What it is**: Average time issues spend in "New" state (freshly created, not yet triaged)
- **Example**: 0.5d means issues typically wait half a day before being triaged
- **Why it matters**: High values suggest backlog grooming delays

#### To Do State Avg Time

- **What it is**: Average time issues spend in "To Do" state (triaged but not started)
- **Example**: 3.2d means issues wait 3.2 days after triage before work begins
- **Why it matters**: Indicates queue time; high values suggest resource constraints or prioritization issues

#### In Progress State Avg Time

- **What it is**: Average time issues spend actively being worked on
- **Example**: 5.5d means active development typically takes 5.5 days
- **Why it matters**: Core development efficiency metric; directly impacted by coding speed and tools

#### Review State Avg Time

- **What it is**: Average time issues spend in code review
- **Example**: 1.2d means code reviews take 1.2 days on average
- **Why it matters**: High values indicate review bottlenecks or insufficient reviewer capacity

#### Release Pending State Avg Time

- **What it is**: Average time issues wait for deployment/release
- **Example**: 2.0d means features wait 2 days to be deployed
- **Why it matters**: Indicates deployment frequency and release process efficiency

#### Waiting State Avg Time

- **What it is**: Average time issues spend blocked or waiting for external dependencies
- **Example**: 4.5d means blocked issues wait 4.5 days for resolution
- **Why it matters**: High values suggest dependency management issues

### Re-entry Rate Metrics

Re-entry rates measure workflow instability and rework.

**How Re-entry Rates are Calculated:**

1. For each issue, count how many times it entered each state
2. Calculate average: `Re-entry Rate = Total State Entries / Number of Issues`
3. A rate of 1.0 means each issue entered that state exactly once (ideal)
4. A rate > 1.0 means issues frequently return to that state (rework)

**Common Re-entry Metrics:**

#### To Do Re-entry Rate

- **What it is**: Average number of times issues return to "To Do" state
- **Example**: 1.5x means issues return to "To Do" an average of 1.5 times
- **Why it matters**: Values > 1.0 indicate scope changes or requirements clarification after work started

#### In Progress Re-entry Rate

- **What it is**: Average number of times issues return to "In Progress" state
- **Example**: 2.0x means issues are actively worked on in 2 separate periods on average
- **Why it matters**: High values suggest failed reviews, bugs found during testing, or work interruptions

#### Review Re-entry Rate

- **What it is**: Average number of times issues return to "Review" state
- **Example**: 1.8x means code typically goes through review 1.8 times
- **Why it matters**: Values > 1.0 indicate changes requested during review; very high values suggest code quality issues

#### Waiting Re-entry Rate

- **What it is**: Average number of times issues become blocked
- **Example**: 1.2x means issues get blocked 1.2 times on average
- **Why it matters**: Indicates dependency management and planning quality

### Issue Type Distribution

#### Story Percentage

- **What it is**: Percentage of completed issues that are "Story" type (user-facing features)
- **How it's calculated**: `(Story Count / Total Issues) × 100%`
- **Example**: 45.5% means nearly half of work is new features
- **Why it matters**: Shows balance between feature development vs other work

#### Task Percentage

- **What it is**: Percentage of completed issues that are "Task" type (technical work, non-user-facing)
- **Example**: 30.0% means 30% of work is technical tasks
- **Why it matters**: High task percentage may indicate technical debt work or infrastructure improvements

#### Bug Percentage

- **What it is**: Percentage of completed issues that are "Bug" type
- **Example**: 20.0% means one-fifth of effort goes to bug fixes
- **Why it matters**: High bug percentage may indicate code quality issues; lower values after AI adoption suggest better code quality

#### Epic Percentage

- **What it is**: Percentage of completed issues that are "Epic" type (large initiatives)
- **Example**: 4.5%
- **Why it matters**: Usually low percentage; tracks major project milestones

### Interpreting Metrics

**Positive AI Impact Indicators:**

- ↓ Average Closure Time (faster completion)
- ↓ In Progress State Time (faster development)
- ↓ Review State Time (fewer review cycles or better code quality)
- ↑ Daily Throughput (all variants) (more work completed)
- ↓ Re-entry Rates (less rework, better quality on first attempt)
- ↓ Bug Percentage (better code quality)

**Comparing Daily Throughput Metrics:**

- **Team baseline**: Use "Daily Throughput" for simple team-level period-to-period comparison
- **Accounting for vacation**: Use "Daily Throughput (skip leave days)" when leave varies significantly
- **Cross-team comparison**: Use "Daily Throughput (average per capacity)" to compare teams of different sizes
- **Most accurate productivity**: Use "Daily Throughput (average per capacity, excl. leave)" for the most accurate per-capacity productivity measurement

**Things to Watch:**

- If Average Closure Time decreases but Bug Percentage increases → speed at cost of quality
- If In Progress time decreases significantly → direct AI coding assistance working
- If Review Re-entry Rate decreases → code quality improvements (fewer change requests)
- If Waiting State time increases → may indicate external dependencies, not tool-related
- **For team reports**: If capacity decreases (members leaving) but throughput stays constant → remaining team became more productive
