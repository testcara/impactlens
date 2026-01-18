"""
Jira Report Generator

Generates text and JSON reports from Jira metrics.
Extracted from cli/get_jira_metrics.py and cli/generate_jira_comparison_report.py
"""

import os
import json
import re
from datetime import datetime

from impactlens.utils.report_utils import (
    normalize_username,
    calculate_percentage_change,
    format_metric_changes,
    add_metric_change,
    add_throughput_metric_change,
    get_identifier_for_file,
    get_identifier_for_display,
    generate_comparison_report_header,
    save_report_output,
    METRICS_GUIDE_URL,
)
from impactlens.utils.core_utils import calculate_days_between, calculate_throughput_variants


class JiraReportGenerator:
    """Generates reports from Jira metrics data."""

    def generate_text_report(
        self,
        metrics,
        jql_query,
        project_key,
        assignee=None,
        start_date=None,
        end_date=None,
        leave_days=0,
        capacity=1.0,
        hide_individual_names=False,
    ):
        """
        Generate human-readable text report from metrics.

        Args:
            metrics: Metrics dictionary from JiraMetricsCalculator
            jql_query: JQL query used
            project_key: Project key
            assignee: Optional assignee filter
            start_date: Phase start date (YYYY-MM-DD) for Data Span calculation
            end_date: Phase end date (YYYY-MM-DD) for Data Span calculation
            leave_days: Number of leave days
            capacity: Work capacity (0.0 to 1.0, default 1.0 = full time)
            hide_individual_names: If True, anonymize assignee and hide JQL query

        Returns:
            String report
        """
        report_lines = []
        report_lines.append("=" * 100)
        if assignee:
            display_assignee = get_identifier_for_display(assignee, hide_individual_names)
            report_lines.append(f"JIRA Data Analysis Report - {display_assignee}")
        else:
            report_lines.append("JIRA Data Analysis Report")
        report_lines.append("=" * 100)
        report_lines.append(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"Project: {project_key}")
        if assignee:
            display_assignee = get_identifier_for_display(assignee, hide_individual_names)
            report_lines.append(f"Assignee: {display_assignee}")
        if not hide_individual_names:
            report_lines.append(f"JQL Query: {jql_query}\n")
        else:
            report_lines.append("")  # Empty line to maintain formatting

        # Data Time Range
        report_lines.append("\n--- Data Time Range ---")

        if start_date and end_date:
            # Show phase configuration dates
            report_lines.append(f"Start: {start_date}")
            report_lines.append(f"End: {end_date}")

            # Calculate phase days
            phase_days = calculate_days_between(start_date, end_date, inclusive=True)

            # Show leave days info
            if leave_days > 0:
                report_lines.append(f"Leave Days: {leave_days} days")
            else:
                report_lines.append(f"Leave Days: 0 days")

            # Show capacity
            report_lines.append(f"Capacity: {capacity}")

            # Data Span is always END - START (inclusive)
            report_lines.append(f"Data Span: {phase_days} days")
        else:
            # Fallback when no phase dates provided
            report_lines.append("Start: N/A")
            report_lines.append("End: N/A")
            report_lines.append("Leave Days: 0 days")
            report_lines.append("Capacity: 1.0")
            report_lines.append("Data Span: N/A")

        # Issue type statistics
        report_lines.append("\n--- Issue Type Statistics ---")
        total_issues = metrics.get("total_issues", 0)
        issue_types = metrics.get("issue_types", {})

        report_lines.append(f"Total: {total_issues} issues")
        if issue_types:
            sorted_types = sorted(issue_types.items(), key=lambda x: x[1], reverse=True)
            for issue_type, count in sorted_types:
                percentage = (count / total_issues) * 100 if total_issues > 0 else 0
                report_lines.append(f"  {issue_type:<20} {count:>5} ({percentage:>5.1f}%)")

        # Task Closure Time Statistics
        closing_times = metrics.get("closing_times", [])
        report_lines.append("\n--- Task Closure Time Statistics ---")

        if closing_times:
            avg_closing_time_seconds = sum(closing_times) / len(closing_times)
            avg_closing_time_days = avg_closing_time_seconds / (24 * 3600)
            avg_closing_time_hours = avg_closing_time_seconds / 3600
            min_time_days = min(closing_times) / (24 * 3600)
            max_time_days = max(closing_times) / (24 * 3600)

            report_lines.append(f"Successfully analyzed issues: {len(closing_times)}")
            report_lines.append(
                f"Average Closure Time: {avg_closing_time_days:.2f} days ({avg_closing_time_hours:.2f} hours)"
            )
            report_lines.append(f"Shortest Closure Time: {min_time_days:.2f} days")
            report_lines.append(f"Longest Closure Time: {max_time_days:.2f} days")
        else:
            report_lines.append("Successfully analyzed issues: 0")
            report_lines.append("Average Closure Time: N/A")
            report_lines.append("Shortest Closure Time: N/A")
            report_lines.append("Longest Closure Time: N/A")

        # State Duration Analysis
        report_lines.append("\n--- State Duration Analysis ---")
        state_stats = metrics.get("state_stats", {})

        if state_stats:
            sorted_states = sorted(
                state_stats.items(),
                key=lambda x: x[1]["total_seconds"] / x[1]["issue_count"],
                reverse=True,
            )

            report_lines.append(f"\nAnalyzed {total_issues} issues state transitions")
            report_lines.append(
                f"\n{'State':<20} {'Occurrences':<12} {'Issues Affected':<15} {'Avg Duration':<20} {'Total Duration':<20}"
            )
            report_lines.append("=" * 100)

            for state, stats in sorted_states:
                avg_seconds = stats["total_seconds"] / stats["issue_count"]
                avg_days = avg_seconds / (24 * 3600)
                avg_hours = avg_seconds / 3600
                total_days = stats["total_seconds"] / (24 * 3600)
                total_hours = stats["total_seconds"] / 3600

                if avg_days >= 1:
                    avg_time_str = f"{avg_days:.2f} days"
                else:
                    avg_time_str = f"{avg_hours:.2f} hours"

                if total_days >= 1:
                    total_time_str = f"{total_days:.2f} days"
                else:
                    total_time_str = f"{total_hours:.2f} hours"

                report_lines.append(
                    f"{state:<20} {stats['total_count']:<12} {stats['issue_count']:<15} {avg_time_str:<20} {total_time_str:<20}"
                )

            # Detailed State Analysis
            report_lines.append("\n--- Detailed State Analysis ---")
            for state, stats in sorted_states:
                avg_transitions = stats["total_count"] / stats["issue_count"]
                report_lines.append(f"\n{state}:")
                report_lines.append(f"  - {stats['issue_count']} issues experienced this state")
                report_lines.append(
                    f"  - Average times per issue entering this state {avg_transitions:.2f} times"
                )
                if avg_transitions > 1.5:
                    report_lines.append(
                        "  ⚠️  Warning: This state was entered multiple times, indicating possible back-and-forth transitions"
                    )
        else:
            report_lines.append("\nAnalyzed 0 issues state transitions")
            report_lines.append(
                f"\n{'State':<20} {'Occurrences':<12} {'Issues Affected':<15} {'Avg Duration':<20} {'Total Duration':<20}"
            )
            report_lines.append("=" * 100)
            report_lines.append("(No state data available)")
            report_lines.append("\n--- Detailed State Analysis ---")
            report_lines.append("\n(No detailed state data available - 0 issues analyzed)")

        return "\n".join(report_lines)

    def generate_json_output(
        self,
        metrics,
        jql_query,
        project_key,
        start_date,
        end_date,
        assignee=None,
        velocity_stats=None,
        hide_individual_names=False,
        leave_days=0,
        capacity=1.0,
    ):
        """
        Generate JSON output from metrics.

        Args:
            metrics: Metrics dictionary
            jql_query: JQL query used
            project_key: Project key
            start_date: Start date string
            end_date: End date string
            assignee: Optional assignee
            velocity_stats: Optional velocity statistics
            hide_individual_names: If True, anonymize assignee and hide JQL

        Returns:
            Dictionary suitable for JSON serialization
        """
        closing_times = metrics.get("closing_times", [])

        # Anonymize assignee if needed (keep JQL for reproducibility)
        display_assignee = (
            get_identifier_for_display(assignee, hide_individual_names) if assignee else None
        )

        # Calculate span_days from start_date and end_date
        from impactlens.utils.core_utils import calculate_days_between

        span_days = calculate_days_between(start_date, end_date) if start_date and end_date else 0

        output_data = {
            "analysis_date": datetime.now().isoformat(),
            "project_key": project_key,
            "query_parameters": {
                "start_date": start_date,
                "end_date": end_date,
                "assignee": display_assignee,  # Anonymized
            },
            "jql_queries": {
                "main_analysis": jql_query,  # Keep original for reproducibility
            },
            "jql_query": jql_query,  # Keep original for reproducibility
            "total_issues_analyzed": metrics.get("total_issues", 0),
            "closing_time_stats": {},
            "state_statistics": {},
            "velocity_stats": velocity_stats or {},
            "issue_types": {},
            # Add time range information (needed for comparison reports)
            "time_range": {
                "start_date": start_date,
                "end_date": end_date,
                "span_days": span_days,
                "leave_days": leave_days,
                "capacity": capacity,
            },
            # Add throughput data (calculated in get_jira_metrics.py)
            "daily_throughput": metrics.get("daily_throughput", 0),
            "daily_throughput_skip_leave": metrics.get("daily_throughput_skip_leave"),
            "daily_throughput_capacity": metrics.get("daily_throughput_capacity"),
            "daily_throughput_both": metrics.get("daily_throughput_both"),
        }

        # Add closing time stats
        if closing_times:
            avg_closing_time_seconds = sum(closing_times) / len(closing_times)
            output_data["closing_time_stats"] = {
                "average_days": avg_closing_time_seconds / (24 * 3600),
                "average_hours": avg_closing_time_seconds / 3600,
                "min_days": min(closing_times) / (24 * 3600),
                "max_days": max(closing_times) / (24 * 3600),
            }

        # Add state statistics
        state_stats = metrics.get("state_stats", {})
        for state, stats in state_stats.items():
            avg_seconds = stats["total_seconds"] / stats["issue_count"]
            output_data["state_statistics"][state] = {
                "total_count": stats["total_count"],
                "issue_count": stats["issue_count"],
                "average_seconds": avg_seconds,
                "average_days": avg_seconds / (24 * 3600),
                "average_hours": avg_seconds / 3600,
                "total_seconds": stats["total_seconds"],
                "avg_transitions_per_issue": stats["total_count"] / stats["issue_count"],
            }

        # Add issue type statistics with counts and percentages
        issue_types = metrics.get("issue_types", {})
        total_issues = metrics.get("total_issues", 0)
        for issue_type, count in issue_types.items():
            percentage = (count / total_issues * 100) if total_issues > 0 else 0
            output_data["issue_types"][issue_type] = {
                "count": count,
                "percentage": percentage,
            }

        return output_data

    def save_text_report(
        self,
        report_text,
        start_date,
        end_date,
        assignee=None,
        output_dir="reports/jira",
        hide_individual_names=False,
    ):
        """
        Save text report to file.

        Args:
            report_text: Report text content
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            assignee: Optional assignee (for filename)
            output_dir: Output directory
            hide_individual_names: If True, anonymize the filename

        Returns:
            Output filename
        """
        return save_report_output(
            content=report_text,
            start_date=start_date,
            end_date=end_date,
            report_type="jira",
            output_format="txt",
            identifier=assignee,
            output_dir=output_dir,
            hide_individual_names=hide_individual_names,
        )

    def save_json_output(
        self,
        output_data,
        start_date,
        end_date,
        assignee=None,
        output_dir="reports/jira",
        hide_individual_names=False,
    ):
        """
        Save JSON output to file.

        Args:
            output_data: Data dictionary
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            assignee: Optional assignee
            output_dir: Output directory
            hide_individual_names: If True, anonymize the filename

        Returns:
            Output filename
        """
        return save_report_output(
            content=json.dumps(output_data, indent=2, ensure_ascii=False),
            start_date=start_date,
            end_date=end_date,
            report_type="jira",
            output_format="json",
            identifier=assignee,
            output_dir=output_dir,
            hide_individual_names=hide_individual_names,
        )

    def parse_jira_report(self, filename):
        """
        Parse a Jira JSON report file and extract key metrics.

        Args:
            filename: Path to JSON report file

        Returns:
            Dictionary with extracted metrics (same structure as PR report parsing)
        """
        with open(filename, "r", encoding="utf-8") as f:
            json_data = json.load(f)

        # Extract data from JSON (same structure as we write in generate_json_output)
        data = {
            "filename": filename,
            "assignee": json_data.get("query_parameters", {}).get("assignee"),
            "jql_query": json_data.get("jql_query"),
            "total_issues": json_data.get("total_issues_analyzed", 0),
            "closure_stats": {},
            "state_times": {},
            "state_reentry": {},
            "time_range": {},
            "issue_types": {},
        }

        # Extract closure stats
        closing_stats = json_data.get("closing_time_stats", {})
        if closing_stats:
            data["closure_stats"]["avg_days"] = closing_stats.get("average_days", 0)
            data["closure_stats"]["max_days"] = closing_stats.get("max_days", 0)

        # Extract state times (convert from state_statistics)
        state_stats = json_data.get("state_statistics", {})
        for state, stats in state_stats.items():
            avg_days = stats.get("average_days", 0)
            if avg_days > 0:
                data["state_times"][state] = avg_days

            # Extract re-entry rates from avg_transitions_per_issue
            reentry_rate = stats.get("avg_transitions_per_issue", 0)
            if reentry_rate > 0:
                data["state_reentry"][state] = reentry_rate

        # Extract time range from time_range field (new format) or query_parameters (fallback)
        time_range = json_data.get("time_range", {})
        if time_range:
            data["time_range"]["start_date"] = time_range.get("start_date")
            data["time_range"]["end_date"] = time_range.get("end_date")
            data["time_range"]["span_days"] = time_range.get("span_days")
            data["time_range"]["leave_days"] = time_range.get("leave_days", 0)
            data["time_range"]["capacity"] = time_range.get("capacity", 1.0)
        else:
            # Fallback to query_parameters for older JSON files
            query_params = json_data.get("query_parameters", {})
            if query_params:
                data["time_range"]["start_date"] = query_params.get("start_date")
                data["time_range"]["end_date"] = query_params.get("end_date")

        # Extract throughput data (already calculated and stored in JSON)
        data["daily_throughput"] = json_data.get("daily_throughput", 0)
        data["daily_throughput_skip_leave"] = json_data.get("daily_throughput_skip_leave")
        data["daily_throughput_capacity"] = json_data.get("daily_throughput_capacity")
        data["daily_throughput_both"] = json_data.get("daily_throughput_both")

        # Extract issue types with count and percentage
        issue_types = json_data.get("issue_types", {})
        for issue_type, stats in issue_types.items():
            data["issue_types"][issue_type] = {
                "count": stats.get("count", 0),
                "percentage": stats.get("percentage", 0),
            }

        return data

    def generate_comparison_tsv(
        self, reports, phase_names, assignee=None, phase_configs=None, project_key=None
    ):
        """
        Generate TSV comparison report from multiple phase reports.

        Args:
            reports: List of parsed report dictionaries
            phase_names: List of phase names
            assignee: Optional assignee
            phase_configs: Optional list of (name, start_date, end_date) tuples from config (for displaying phase dates)

        Returns:
            TSV format string
        """
        # Generate common header using shared utility
        lines = generate_comparison_report_header(
            report_type="JIRA",
            identifier=assignee,
            project_info=project_key,
            reports=reports,
            phase_names=phase_names,
        )

        # Metrics table header
        header = "Metric\t" + "\t".join(phase_names)
        lines.append(header)

        # Period duration (always use Data Span from individual reports)
        periods = []
        for r in reports:
            span_days = r["time_range"].get("span_days")
            if span_days is not None:
                periods.append(f"{span_days}d")
            else:
                periods.append("N/A")
        lines.append("Analysis Period\t" + "\t".join(periods))

        # Leave days
        leave_days_list = []
        for r in reports:
            leave_days = r["time_range"].get("leave_days", 0)
            # Format as int if it's a whole number, otherwise as float
            if isinstance(leave_days, float) and leave_days == int(leave_days):
                leave_days_list.append(str(int(leave_days)))
            else:
                leave_days_list.append(str(leave_days))
        lines.append("Leave Days\t" + "\t".join(leave_days_list))

        # Capacity
        capacity_list = []
        for r in reports:
            capacity = r["time_range"].get("capacity", 1.0)
            capacity_list.append(str(capacity))
        lines.append("Capacity\t" + "\t".join(capacity_list))

        # Total issues
        issues = [str(r["total_issues"]) for r in reports]
        lines.append("Total Issues Completed\t" + "\t".join(issues))

        # Average closure time
        avg_times = [r["closure_stats"].get("avg_days", 0) for r in reports]
        lines.append("Average Closure Time\t" + "\t".join(f"{t:.2f}d" for t in avg_times))

        # Longest closure time
        max_times = [r["closure_stats"].get("max_days", 0) for r in reports]
        lines.append("Longest Closure Time\t" + "\t".join(f"{t:.2f}d" for t in max_times))

        # Daily throughput variants - using shared utility function
        throughputs_skip_leave = []
        throughputs_capacity = []
        throughputs_both = []

        for i, report in enumerate(reports):
            period = periods[i]
            if period != "N/A" and period.endswith("d"):
                analysis_days = int(period.replace("d", ""))
                leave_days = report["time_range"].get("leave_days", 0)
                capacity = report["time_range"].get("capacity", 1.0)
                total_issues = report["total_issues"]

                # Calculate all variants using shared function
                variants = calculate_throughput_variants(
                    total_issues, analysis_days, leave_days=leave_days, capacity=capacity
                )

                # Format each variant
                throughputs_skip_leave.append(
                    f"{variants['skip_leave']:.2f}/d"
                    if variants["skip_leave"] is not None
                    else "N/A"
                )
                throughputs_capacity.append(
                    f"{variants['capacity']:.2f}/d" if variants["capacity"] is not None else "N/A"
                )
                throughputs_both.append(
                    f"{variants['both']:.2f}/d" if variants["both"] is not None else "N/A"
                )
            else:
                throughputs_skip_leave.append("N/A")
                throughputs_capacity.append("N/A")
                throughputs_both.append("N/A")

        lines.append("Daily Throughput (skip leave days)\t" + "\t".join(throughputs_skip_leave))
        lines.append("Daily Throughput (average per capacity)\t" + "\t".join(throughputs_capacity))
        lines.append(
            "Daily Throughput (average per capacity, excl. leave)\t" + "\t".join(throughputs_both)
        )

        # Daily throughput = Total Issues / Analysis Period
        throughputs = []
        for i, report in enumerate(reports):
            period = periods[i]
            if period != "N/A" and period.endswith("d"):
                analysis_days = int(period.replace("d", ""))
                throughput = report["total_issues"] / analysis_days if analysis_days > 0 else 0
                throughputs.append(f"{throughput:.2f}/d")
            else:
                throughputs.append("N/A")
        lines.append("Daily Throughput\t" + "\t".join(throughputs))

        # State times
        state_names = ["New", "To Do", "In Progress", "Review", "Release Pending", "Waiting"]
        for state in state_names:
            values = []
            for report in reports:
                time = report["state_times"].get(state, 0)
                values.append(f"{time:.2f}d" if time > 0 else "N/A")
            lines.append(f"{state} State Avg Time\t" + "\t".join(values))

        # Re-entry rates
        reentry_states = ["To Do", "In Progress", "Review", "Waiting"]
        for state in reentry_states:
            values = []
            for report in reports:
                rate = report["state_reentry"].get(state, 0)
                values.append(f"{rate:.2f}x" if rate > 0 else "N/A")
            lines.append(f"{state} Re-entry Rate\t" + "\t".join(values))

        # Issue types
        issue_types = ["Story", "Task", "Bug", "Epic"]
        for itype in issue_types:
            values = []
            for report in reports:
                if itype in report["issue_types"]:
                    values.append(f"{report['issue_types'][itype]['percentage']:.2f}%")
                else:
                    values.append("0.00%")
            lines.append(f"{itype} Percentage\t" + "\t".join(values))

        lines.append("")
        lines.append(
            "Note: N/A values indicate no issues entered that workflow state during the period."
        )
        lines.append(
            "This can be positive (e.g., no blocked issues) or indicate the state isn't used in your workflow."
        )

        # Calculate metric changes (first phase vs last phase) - only if we have 2+ reports
        if len(reports) >= 2:
            lines.append("")
            lines.append("Key Changes:")

            first_report = reports[0]
            last_report = reports[-1]

            # Collect all metric changes using shared utility functions
            metric_changes = []

            # Daily throughput metrics - use shared utility function
            # (Now both Jira and PR reports have the same throughput data structure)
            add_throughput_metric_change(metric_changes, first_report, last_report)

            # Average closure time
            first_avg = first_report["closure_stats"].get("avg_days", 0)
            last_avg = last_report["closure_stats"].get("avg_days", 0)
            add_metric_change(metric_changes, "Average Closure Time", first_avg, last_avg, "d")

            # State times
            for state in state_names:
                first_time = first_report["state_times"].get(state, 0)
                last_time = last_report["state_times"].get(state, 0)
                add_metric_change(metric_changes, f"{state} State", first_time, last_time, "d")

            # Re-entry rates
            for state in reentry_states:
                first_rate = first_report["state_reentry"].get(state, 0)
                last_rate = last_report["state_reentry"].get(state, 0)
                add_metric_change(
                    metric_changes, f"{state} Re-entry Rate", first_rate, last_rate, "x"
                )

            # Format and append the top changes using shared utility
            formatted_changes = format_metric_changes(metric_changes, top_n=5)
            lines.extend(formatted_changes)

        lines.append("")
        lines.append("For detailed metric explanations, see:")
        lines.append(METRICS_GUIDE_URL)

        return "\n".join(lines)
