"""
AI Report Analyzer

Analyzes TSV reports using LLM to provide data-driven insights.
Model-agnostic design supporting OpenAI-compatible APIs.
"""

import csv
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime

from ai_impact_analysis.utils.report_utils import calculate_percentage_change


class ReportPreprocessor:
    """Preprocesses TSV reports to extract key metrics and trends."""

    def __init__(self, tsv_file_path: str):
        """
        Initialize preprocessor with TSV report.

        Args:
            tsv_file_path: Path to the combined TSV report
        """
        self.tsv_file_path = tsv_file_path
        self.report_type = None  # 'github' or 'jira'
        self.phases = []  # List of phase names
        self.metrics = {}  # Dict of metric_name -> {phase -> {member -> value}}
        self.team_column = "team"  # Column name for team aggregated data

    def load_and_parse(self) -> Dict[str, Any]:
        """
        Load TSV file and parse into structured data.

        Returns:
            Dict containing:
                - report_type: 'github' or 'jira'
                - phases: List of phase names
                - metrics: Structured metrics data
                - summary: Preprocessed summary for LLM
        """
        with open(self.tsv_file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Detect report type
        if "GitHub PR AI Impact Analysis" in content:
            self.report_type = "github"
        elif "Jira AI Impact Analysis" in content:
            self.report_type = "jira"
        else:
            raise ValueError("Unknown report type")

        # Parse metrics sections
        self._parse_tsv_content(content)

        # Generate summary
        summary = self._generate_summary()

        return {
            "report_type": self.report_type,
            "phases": self.phases,
            "metrics": self.metrics,
            "summary": summary,
        }

    def _parse_tsv_content(self, content: str):
        """Parse TSV content into structured metrics."""
        lines = content.strip().split("\n")

        current_metric = None
        metric_data = []

        for line in lines:
            line = line.strip()

            # Detect metric section headers
            if line.startswith("=== ") and line.endswith(" ==="):
                # Save previous metric
                if current_metric and metric_data:
                    self._process_metric_section(current_metric, metric_data)
                    metric_data = []

                # Extract new metric name
                current_metric = line[4:-4].strip()

            elif line and current_metric:
                # Skip header and metadata lines
                if line.startswith("Phase\t"):
                    # This is the table header row, add it as first line
                    if not metric_data:
                        metric_data.append(line)
                elif not any(
                    line.startswith(x)
                    for x in [
                        "GitHub PR",
                        "Jira AI",
                        "Generated:",
                        "Project:",
                        "This report",
                        "to evaluate",
                        "Phase 1:",
                        "Phase 2:",
                        "Phase 3:",
                    ]
                ):
                    metric_data.append(line)

        # Process last metric
        if current_metric and metric_data:
            self._process_metric_section(current_metric, metric_data)

    def _process_metric_section(self, metric_name: str, data_lines: List[str]):
        """Process a single metric section."""
        if not data_lines:
            return

        # Parse header and data rows
        rows = [line.split("\t") for line in data_lines if line]

        if len(rows) < 2:
            return

        header = rows[0]  # Phase, team, member1, member2, ...
        data_rows = rows[1:]  # Phase data

        # Extract phases and store metric data
        metric_dict = {}

        for row in data_rows:
            if len(row) < 2:
                continue

            phase = row[0].strip()

            # Skip empty phase names
            if not phase:
                continue

            # Store phases from first metric (only if not already stored)
            if phase not in self.phases:
                self.phases.append(phase)

            # Store data for each column (team + individual members)
            phase_data = {}
            for i, value in enumerate(row[1:], start=1):
                if i < len(header):
                    column_name = header[i].strip()
                    phase_data[column_name] = value.strip()

            metric_dict[phase] = phase_data

        self.metrics[metric_name] = metric_dict

    def _generate_summary(self) -> str:
        """Generate a concise summary of key metrics for LLM input."""
        summary_lines = []

        summary_lines.append(f"Report Type: {self.report_type.upper()}")
        summary_lines.append(f"Analysis Phases: {', '.join(self.phases)}")
        summary_lines.append(f"Total Metrics Tracked: {len(self.metrics)}")
        summary_lines.append("")

        # Extract team-level data for key metrics
        summary_lines.append("=== TEAM-LEVEL KEY METRICS (Across Phases) ===")
        summary_lines.append("")

        key_metrics = self._identify_key_metrics()

        for metric_name in key_metrics:
            if metric_name not in self.metrics:
                continue

            summary_lines.append(f"--- {metric_name} ---")

            metric_data = self.metrics[metric_name]

            for phase in self.phases:
                if phase not in metric_data:
                    continue

                phase_data = metric_data[phase]
                team_value = phase_data.get(self.team_column, "N/A")

                summary_lines.append(f"{phase}: {team_value}")

            # Calculate trend
            trend = self._calculate_trend(metric_name)
            if trend:
                summary_lines.append(f"Trend: {trend}")

            summary_lines.append("")

        return "\n".join(summary_lines)

    def _identify_key_metrics(self) -> List[str]:
        """Identify the most important metrics based on report type."""
        if self.report_type == "github":
            return [
                "Total PRs Merged (excl. bot-authored)",
                "AI Adoption Rate",
                "Avg Time to Merge per PR (days)",
                "Avg Time to First Review (hours)",
                "Avg Changes Requested",
                "Avg Comments (excl. bots & approvals)",
                "Avg Lines Added",
            ]
        else:  # jira
            return [
                "Total Issues Completed",
                "Average Closure Time",
                "Daily Throughput (considering leave days + capacity)",
                "In Progress State Avg Time",
                "Review State Avg Time",
                "Review Re-entry Rate",
                "Bug Percentage",
            ]

    def _calculate_trend(self, metric_name: str) -> Optional[str]:
        """Calculate trend for a metric across phases."""
        if metric_name not in self.metrics:
            return None

        metric_data = self.metrics[metric_name]
        values = []

        for phase in self.phases:
            if phase not in metric_data:
                continue

            team_value = metric_data[phase].get(self.team_column, "N/A")

            # Try to parse numeric value
            try:
                # Handle percentages
                if "%" in team_value:
                    numeric_val = float(team_value.rstrip("%"))
                # Handle 'd' suffix (days)
                elif team_value.endswith("d"):
                    numeric_val = float(team_value[:-1])
                # Handle 'h' suffix (hours)
                elif team_value.endswith("h"):
                    numeric_val = float(team_value[:-1])
                # Handle 'x' suffix (re-entry rates)
                elif team_value.endswith("x"):
                    numeric_val = float(team_value[:-1])
                # Plain numbers
                else:
                    numeric_val = float(team_value)

                values.append(numeric_val)
            except (ValueError, AttributeError):
                # Skip non-numeric values
                pass

        if len(values) < 2:
            return None

        # Calculate percentage change from first to last
        first_val = values[0]
        last_val = values[-1]

        if first_val == 0:
            if last_val == 0:
                return "Stable (no change)"
            else:
                return f"Increased significantly (from 0 to {last_val:.2f})"

        # Reuse the common percentage change calculation
        pct_change = calculate_percentage_change(first_val, last_val)
        if pct_change is None:
            return None

        if abs(pct_change) < 5:
            return "Stable"
        elif pct_change > 0:
            return f"↑ Increased by {pct_change:.1f}%"
        else:
            return f"↓ Decreased by {abs(pct_change):.1f}%"
