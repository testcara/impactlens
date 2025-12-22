"""Utilities module for common helper functions."""

from impactlens.utils.logger import logger
from impactlens.utils.report_utils import (
    normalize_username,
    calculate_percentage_change,
    format_metric_changes,
    add_metric_change,
)
from impactlens.utils.workflow_utils import (
    Colors,
    get_project_root,
    load_config_file,
    cleanup_old_reports,
    upload_to_google_sheets,
    find_latest_comparison_report,
)
from impactlens.utils.anonymization import (
    NameAnonymizer,
    anonymize_names_in_list,
    anonymize_member_data,
    get_display_member_info,
    should_include_sensitive_fields,
)

__all__ = [
    "logger",
    "normalize_username",
    "calculate_percentage_change",
    "format_metric_changes",
    "add_metric_change",
    "Colors",
    "get_project_root",
    "load_config_file",
    "cleanup_old_reports",
    "upload_to_google_sheets",
    "find_latest_comparison_report",
    "NameAnonymizer",
    "anonymize_names_in_list",
    "anonymize_member_data",
    "get_display_member_info",
    "should_include_sensitive_fields",
]
