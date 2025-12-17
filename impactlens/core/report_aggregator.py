"""
Report Aggregator

Aggregates multiple combined reports (Jira/PR) into a unified report.
Reads already-generated TSV files and merges them.
"""

import os
import glob
import yaml
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from impactlens.utils.logger import logger


class ReportAggregator:
    """Aggregates multiple combined reports into unified reports."""

    def __init__(self, config_path: str):
        """
        Initialize report aggregator.

        Args:
            config_path: Path to aggregation config file
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.agg_settings = self.config.get("aggregation", {})
        self.name = self.agg_settings.get("name", "Aggregated Report")
        self.output_dir = Path(self.agg_settings.get("output_dir", "reports/aggregated"))

    def _load_config(self) -> Dict[str, Any]:
        """Load aggregation config from YAML file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Aggregation config not found: {self.config_path}")

        with open(self.config_path, "r") as f:
            return yaml.safe_load(f)

    def find_reports(self, report_type: str = "jira") -> List[Path]:
        """
        Find reports to aggregate based on config.

        Args:
            report_type: 'jira' or 'pr'

        Returns:
            List of report file paths
        """
        reports = []

        # Check if manual reports are specified
        manual_reports = self.config.get("manual_reports", {})
        if manual_reports and report_type in manual_reports:
            # Use manually specified reports
            for pattern in manual_reports[report_type]:
                found = glob.glob(str(pattern))
                reports.extend([Path(p) for p in found])
            logger.info(f"Found {len(reports)} {report_type} reports (manual specification)")
            return reports

        # Auto-discover reports from projects
        projects = self.agg_settings.get("projects", [])
        excludes = self.agg_settings.get("exclude", []) or []  # Ensure it's a list, not None

        for project in projects:
            # Check if excluded
            exclude_key = f"{project}/{report_type}"
            if exclude_key in excludes:
                logger.info(f"Excluding {exclude_key} as specified in config")
                continue

            # Build search pattern
            if report_type == "jira":
                pattern = f"reports/{project}/jira/combined_jira_report_*.tsv"
            else:  # pr
                pattern = f"reports/{project}/github/combined_pr_report_*.tsv"

            # Find matching files
            found = glob.glob(pattern)
            if found:
                # Use the most recent file if multiple found
                latest = max(found, key=os.path.getmtime)
                reports.append(Path(latest))
                logger.info(f"Found {report_type} report for {project}: {Path(latest).name}")
            else:
                logger.warning(f"No {report_type} report found for {project} (pattern: {pattern})")

        logger.info(f"Total {report_type} reports to aggregate: {len(reports)}")
        return reports

    def parse_combined_report(self, report_path: Path, report_type: str) -> Dict[str, Any]:
        """
        Parse a combined report TSV file.

        Args:
            report_path: Path to combined report TSV
            report_type: 'jira' or 'pr'

        Returns:
            Parsed report data structure
        """
        logger.info(f"Parsing {report_type} report: {report_path.name}")

        with open(report_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # Extract metadata and phases from header
        phases = []
        members = []
        project_name = None

        # Parse header to find project name and phases
        for i, line in enumerate(lines[:20]):  # Check first 20 lines for metadata
            if "Project:" in line:
                project_name = line.split("Project:")[-1].strip()
            elif line.startswith("Phase "):
                # Extract phase info
                pass

        # Find the first metric section to get structure
        metrics_data = {}
        current_metric = None
        phase_row_found = False

        for line in lines:
            stripped = line.strip()

            # Detect metric section headers
            if stripped.startswith("=== ") and stripped.endswith(" ==="):
                current_metric = stripped[4:-4]  # Remove === markers
                metrics_data[current_metric] = {}
                phase_row_found = False
                continue

            # Skip empty lines and non-data lines
            if not stripped or not current_metric:
                continue

            # Parse data rows (tab-separated)
            if "\t" in line:
                parts = [p.strip() for p in line.split("\t")]

                # First data row after metric header contains column headers
                if not phase_row_found and parts[0] == "Phase":
                    # Header row: Phase | team | Developer-XXX | Developer-YYY | ...
                    members = parts[2:] if len(parts) > 2 else []
                    phase_row_found = True
                    continue

                # Data rows
                if parts[0] and parts[0] not in ["Phase", ""]:
                    phase_name = parts[0]
                    if phase_name not in phases:
                        phases.append(phase_name)

                    # Parse values: phase_name | team_value | member1_value | member2_value | ...
                    team_value = parts[1] if len(parts) > 1 else "N/A"
                    member_values = {}

                    for i, member in enumerate(members):
                        if i + 2 < len(parts):
                            member_values[member] = parts[i + 2]
                        else:
                            member_values[member] = "N/A"

                    metrics_data[current_metric][phase_name] = {
                        "team": team_value,
                        "members": member_values,
                    }

        result = {
            "source_file": report_path.name,
            "source_project": project_name or self._extract_project_from_path(report_path),
            "report_type": report_type,
            "phases": phases,
            "members": members,
            "metrics": metrics_data,
        }

        logger.info(
            f"Parsed {len(metrics_data)} metrics, {len(phases)} phases, {len(members)} members"
        )
        return result

    def _extract_project_from_path(self, report_path: Path) -> str:
        """Extract project name from report path."""
        # Try to get project from path: reports/project-name/jira/...
        parts = report_path.parts
        if "reports" in parts:
            idx = parts.index("reports")
            if idx + 1 < len(parts):
                return parts[idx + 1]
        return "Unknown"

    def merge_reports(self, reports_data: List[Dict[str, Any]], report_type: str) -> Dict[str, Any]:
        """
        Merge multiple parsed reports into one aggregated report.

        Args:
            reports_data: List of parsed report data
            report_type: 'jira' or 'pr'

        Returns:
            Merged report data
        """
        if not reports_data:
            raise ValueError("No reports to merge")

        logger.info(f"Merging {len(reports_data)} {report_type} reports")

        # Use first report as template for structure
        template = reports_data[0]
        phases = template["phases"]

        # Collect all unique members across all reports
        all_members = set()
        for data in reports_data:
            all_members.update(data["members"])
        all_members = sorted(all_members)

        # Collect all projects
        projects = [data["source_project"] for data in reports_data]

        # Merge metrics
        merged_metrics = {}

        for metric_name in template["metrics"].keys():
            merged_metrics[metric_name] = {}

            for phase in phases:
                # Collect data for this metric and phase across all projects
                project_values = {}
                member_data = {member: [] for member in all_members}

                for data in reports_data:
                    project = data["source_project"]

                    # Get metric data for this phase
                    if metric_name in data["metrics"] and phase in data["metrics"][metric_name]:
                        phase_data = data["metrics"][metric_name][phase]
                        project_values[project] = phase_data["team"]

                        # Collect member data
                        for member in all_members:
                            if member in phase_data["members"]:
                                value = phase_data["members"][member]
                                if value != "N/A":
                                    member_data[member].append({"value": value, "project": project})

                # Calculate overall value (aggregate across projects)
                overall_value = self._calculate_overall(
                    metric_name, list(project_values.values()), report_type
                )

                # Aggregate member values (if member appears in multiple projects)
                aggregated_members = {}
                for member, values in member_data.items():
                    if not values:
                        aggregated_members[member] = "N/A"
                    elif len(values) == 1:
                        aggregated_members[member] = values[0]["value"]
                    else:
                        # Member appears in multiple projects - aggregate
                        member_values = [v["value"] for v in values]
                        aggregated_members[member] = self._calculate_overall(
                            metric_name, member_values, report_type
                        )

                merged_metrics[metric_name][phase] = {
                    "overall": overall_value,
                    "projects": project_values,
                    "members": aggregated_members,
                }

        return {
            "name": self.name,
            "report_type": report_type,
            "phases": phases,
            "projects": projects,
            "members": all_members,
            "metrics": merged_metrics,
        }

    def _calculate_overall(self, metric_name: str, values: List[str], report_type: str) -> str:
        """
        Calculate overall/aggregated value for a metric.

        Args:
            metric_name: Name of the metric
            values: List of string values to aggregate
            report_type: 'jira' or 'pr'

        Returns:
            Aggregated value as string
        """
        # Filter out N/A values
        valid_values = [v for v in values if v != "N/A" and v != ""]
        if not valid_values:
            return "N/A"

        # Determine aggregation strategy based on metric name
        metric_lower = metric_name.lower()

        # Sum metrics (counts, totals)
        if any(keyword in metric_lower for keyword in ["total", "count", "prs merged", "issues"]):
            try:
                # Extract numeric values
                nums = []
                for v in valid_values:
                    # Handle formats like "150", "0.77/d", "14.26d", "91.18h", "0.0%"
                    v_clean = v.replace("/d", "").replace("d", "").replace("h", "").replace("%", "")
                    nums.append(float(v_clean))
                total = sum(nums)

                # Format based on original format
                if "d" in values[0]:
                    return f"{total:.2f}d"
                elif "h" in values[0]:
                    return f"{total:.2f}h"
                elif "%" in values[0]:
                    return f"{total:.1f}%"
                elif "/d" in values[0]:
                    return f"{total:.2f}/d"
                else:
                    return str(int(total))
            except (ValueError, IndexError):
                return "N/A"

        # Average metrics (times, rates)
        else:
            try:
                nums = []
                for v in valid_values:
                    v_clean = v.replace("/d", "").replace("d", "").replace("h", "").replace("%", "")
                    nums.append(float(v_clean))
                avg = sum(nums) / len(nums)

                # Format based on original format
                if "d" in values[0]:
                    return f"{avg:.2f}d"
                elif "h" in values[0]:
                    return f"{avg:.2f}h"
                elif "%" in values[0]:
                    return f"{avg:.1f}%"
                elif "/d" in values[0]:
                    return f"{avg:.2f}/d"
                else:
                    return f"{avg:.2f}"
            except (ValueError, IndexError):
                return "N/A"

    def generate_aggregated_report(self, merged_data: Dict[str, Any], report_type: str) -> Path:
        """
        Generate aggregated report TSV file.

        Args:
            merged_data: Merged report data
            report_type: 'jira' or 'pr'

        Returns:
            Path to generated report file
        """
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"aggregated_{report_type}_report_{timestamp}.tsv"
        output_path = self.output_dir / filename

        logger.info(f"Generating aggregated {report_type} report: {filename}")

        lines = []

        # Header
        if report_type == "jira":
            lines.append("Jira AI Impact Analysis - Aggregated Report")
        else:
            lines.append("GitHub PR AI Impact Analysis - Aggregated Report")

        lines.append(f"Generated: {datetime.now().strftime('%B %d, %Y')}")
        lines.append(f"Report Name: {merged_data['name']}")
        lines.append(f"Aggregated Projects: {', '.join(merged_data['projects'])}")
        lines.append("")
        lines.append("This report aggregates metrics from multiple projects/repositories.")
        lines.append("")

        # Phase descriptions (if available)
        for i, phase in enumerate(merged_data["phases"], 1):
            lines.append(f"Phase {i}: {phase}")
        lines.append("")

        # Add aggregation note before data
        lines.append("Note: OVERALL column aggregates across all projects.")
        lines.append("      For count/total metrics: sum across projects")
        lines.append("      For average metrics: average across projects")
        lines.append("")

        # Generate metric sections
        for metric_name, metric_data in merged_data["metrics"].items():
            lines.append(f"=== {metric_name} ===")

            # Column headers: Phase | OVERALL | project1 | project2 | ... | member1 | member2 | ...
            headers = ["Phase", "OVERALL"] + merged_data["projects"] + merged_data["members"]
            lines.append("\t".join(headers))

            # Data rows (one per phase)
            for phase in merged_data["phases"]:
                if phase in metric_data:
                    phase_data = metric_data[phase]
                    row = [phase, phase_data["overall"]]

                    # Add project values
                    for project in merged_data["projects"]:
                        row.append(phase_data["projects"].get(project, "N/A"))

                    # Add member values
                    for member in merged_data["members"]:
                        row.append(phase_data["members"].get(member, "N/A"))

                    lines.append("\t".join(row))

            lines.append("")  # Empty line between metrics

        # Write to file
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        logger.info(f"Aggregated report saved to: {output_path}")
        return output_path

    def aggregate_jira_reports(self) -> Optional[Path]:
        """Aggregate Jira reports."""
        logger.info("Starting Jira report aggregation")

        # Find reports
        report_paths = self.find_reports("jira")
        if not report_paths:
            logger.warning("No Jira reports found to aggregate")
            return None

        # Parse reports
        reports_data = []
        for path in report_paths:
            try:
                data = self.parse_combined_report(path, "jira")
                reports_data.append(data)
            except Exception as e:
                logger.error(f"Failed to parse {path}: {e}")
                continue

        if not reports_data:
            logger.error("No valid Jira reports to aggregate")
            return None

        # Merge reports
        merged_data = self.merge_reports(reports_data, "jira")

        # Generate aggregated report
        output_path = self.generate_aggregated_report(merged_data, "jira")

        return output_path

    def aggregate_pr_reports(self) -> Optional[Path]:
        """Aggregate PR reports."""
        logger.info("Starting PR report aggregation")

        # Find reports
        report_paths = self.find_reports("pr")
        if not report_paths:
            logger.warning("No PR reports found to aggregate")
            return None

        # Parse reports
        reports_data = []
        for path in report_paths:
            try:
                data = self.parse_combined_report(path, "pr")
                reports_data.append(data)
            except Exception as e:
                logger.error(f"Failed to parse {path}: {e}")
                continue

        if not reports_data:
            logger.error("No valid PR reports to aggregate")
            return None

        # Merge reports
        merged_data = self.merge_reports(reports_data, "pr")

        # Generate aggregated report
        output_path = self.generate_aggregated_report(merged_data, "pr")

        return output_path

    def aggregate_all(self) -> Dict[str, Optional[Path]]:
        """
        Aggregate both Jira and PR reports.

        Returns:
            Dict with 'jira' and 'pr' keys pointing to output paths
        """
        results = {"jira": self.aggregate_jira_reports(), "pr": self.aggregate_pr_reports()}

        return results
