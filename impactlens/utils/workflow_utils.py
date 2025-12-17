"""
Workflow utilities for report generation scripts.

This module contains shared functions used by Jira and GitHub report generation workflows.
"""

import os
import sys
import glob
import subprocess
import yaml
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime

from impactlens.utils.logger import Colors, set_log_level


def get_project_root() -> Path:
    """
    Get the project root directory by searching for marker files.

    Searches upward from current file for .git directory or other markers.
    """
    current = Path(__file__).resolve()

    # Search upward for project markers
    for parent in [current, *current.parents]:
        # Check for common project root markers
        if any(
            [
                (parent / ".git").exists(),
                (parent / "pyproject.toml").exists(),
                (parent / "setup.py").exists(),
                (parent / "requirements.txt").exists() and (parent / "impactlens").is_dir(),
            ]
        ):
            return parent

    # Fallback: assume current working directory
    return Path.cwd()


def merge_configs(default_config: Dict[str, Any], custom_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge custom configuration with default configuration.

    Custom config values override defaults. Missing values in custom config
    are taken from default config.

    Args:
        default_config: Default configuration dict
        custom_config: Custom configuration dict (overrides defaults)

    Returns:
        Merged configuration dict
    """
    merged = default_config.copy()

    # Override with custom values
    for key, value in custom_config.items():
        if value is not None:  # Only override if value is provided
            merged[key] = value

    return merged


def validate_config_file(
    custom_config_path: Optional[Path], default_config_path: Path, config_type: str = "config"
) -> bool:
    """
    Validate that config files exist and are accessible.

    Design:
    - If custom config specified, it must exist (default is optional for merging)
    - If no custom config, default config must exist
    - If both exist, they will be merged

    Args:
        custom_config_path: Path to custom config file (if specified by user)
        default_config_path: Path to default config file
        config_type: Type of config for error messages (e.g., "PR config", "Jira config")

    Returns:
        True if validation passes, False otherwise (with error message printed)
    """
    # Validate custom config file if specified (it must exist)
    if custom_config_path:
        if not custom_config_path.exists():
            print(
                f"{Colors.RED}Error: Specified {config_type} file does not exist: {custom_config_path}{Colors.NC}"
            )
            print(f"{Colors.YELLOW}Please check the path and try again.{Colors.NC}")
            return False
        if not custom_config_path.is_file():
            print(
                f"{Colors.RED}Error: Specified {config_type} path is not a file: {custom_config_path}{Colors.NC}"
            )
            print(f"{Colors.YELLOW}Please provide a valid config file path.{Colors.NC}")
            return False
        # Custom config exists and is valid
        # Default config is optional (will be used for merging if it exists)
        return True

    # No custom config provided, so default config must exist
    if not default_config_path.exists():
        print(
            f"{Colors.RED}Error: Default {config_type} file not found: {default_config_path}{Colors.NC}"
        )
        print(
            f"{Colors.YELLOW}Please create the config file or specify a custom config with --config{Colors.NC}"
        )
        return False

    return True


def load_and_resolve_config(
    custom_config_path: Optional[Path],
    default_config_path: Path,
    default_reports_dir: Path,
    config_type: str = "config",
) -> Optional[Tuple[List[Tuple[str, str, str]], str, Path, Dict[str, Any]]]:
    """
    Validate, load config file, and resolve output directory.

    This is a convenience function that integrates validation, loading, and output directory resolution.

    Args:
        custom_config_path: Path to custom config file (if specified by user)
        default_config_path: Path to default config file
        default_reports_dir: Default reports directory (e.g., project_root / "reports" / "jira")
        config_type: Type of config for error messages (e.g., "PR config", "Jira config")

    Returns:
        Tuple of (phases, default_assignee_or_author, reports_dir, project_settings) if successful,
        None if validation fails

    Note:
        Prints error messages and returns None on validation or loading errors.
    """
    # Step 1: Validate config files
    if not validate_config_file(custom_config_path, default_config_path, config_type):
        return None

    # Step 2: Load configuration
    try:
        if custom_config_path:
            # Merge custom config with default
            phases, default_assignee_or_author, output_dir, project_settings = load_config_file(
                default_config_path, custom_config_path
            )
        else:
            # Use default config only
            phases, default_assignee_or_author, output_dir, project_settings = load_config_file(
                default_config_path
            )
    except (FileNotFoundError, ValueError) as e:
        print(f"{Colors.RED}Error loading config: {e}{Colors.NC}")
        return None

    # Step 3: Resolve output directory
    if output_dir:
        reports_dir = Path(output_dir)
        print(f"{Colors.BLUE}Using custom output directory: {reports_dir}{Colors.NC}")
    else:
        reports_dir = default_reports_dir

    return phases, default_assignee_or_author, reports_dir, project_settings


def load_config_file(
    config_path: Path, custom_config_path: Optional[Path] = None
) -> Tuple[List[Tuple[str, str, str]], str, Optional[str], Dict[str, Any]]:
    """
    Load phase configuration from a YAML config file with optional custom config override.

    Design:
    1. If custom config exists AND default config exists → merge (custom overrides default)
    2. If custom config exists BUT default config does NOT exist → use custom directly
    3. If default config exists WITHOUT custom config → use default

    Args:
        config_path: Path to default YAML configuration file
        custom_config_path: Optional path to custom YAML config that overrides defaults

    Returns:
        Tuple of (phases, default_assignee, output_dir, project_settings)
        phases: List of (phase_name, start_date, end_date) tuples
        default_assignee: Default assignee/author (empty string for team)
        output_dir: Optional custom output directory for team isolation
        project_settings: Dict with project configuration (jira_url, github_repo_owner, etc.)

    Raises:
        FileNotFoundError: If required config file doesn't exist
        ValueError: If config format is invalid
    """
    config = None

    # Case 1 & 2: Custom config provided
    if custom_config_path and custom_config_path.exists():
        # Load custom config
        try:
            with open(custom_config_path, "r") as f:
                custom_config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML format in {custom_config_path}: {e}")

        if not custom_config:
            raise ValueError(f"Empty config file: {custom_config_path}")

        # Case 1: If default config also exists, merge them (custom overrides default)
        if config_path.exists():
            try:
                with open(config_path, "r") as f:
                    default_config = yaml.safe_load(f)
                if default_config:
                    config = merge_configs(default_config, custom_config)
                    print(
                        f"[INFO] Merged custom config {custom_config_path} with default {config_path}"
                    )
                else:
                    config = custom_config
            except yaml.YAMLError as e:
                print(f"[WARNING] Invalid YAML in default config {config_path}: {e}")
                config = custom_config
        else:
            # Case 2: Only custom config exists, use it directly
            config = custom_config
            print(f"[INFO] Using custom config: {custom_config_path}")

    # Case 3: No custom config, use default
    else:
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        try:
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML format in {config_path}: {e}")

        if not config:
            raise ValueError(f"Empty config file: {config_path}")

        print(f"[INFO] Using default config: {config_path}")

    # Extract phases
    phases = []
    if "phases" in config and config["phases"]:
        for phase in config["phases"]:
            name = phase.get("name", "")
            start = phase.get("start", "")
            end = phase.get("end", "")
            if name and start and end:
                phases.append((name, start, end))

    if not phases:
        raise ValueError(f"No valid phases found in {config_path}")

    # Extract default assignee/author
    default_assignee = config.get("default_assignee", "")

    # Extract custom output directory (for team isolation)
    output_dir = config.get("output_dir", None)

    # Extract project settings (non-sensitive configuration)
    project_settings = config.get("project", {})

    # Apply project settings to environment variables (config overrides env)
    # This allows config files to override .env settings
    env_mappings = {
        "jira_url": "JIRA_URL",
        "jira_project_key": "JIRA_PROJECT_KEY",
        "github_repo_owner": "GITHUB_REPO_OWNER",
        "github_repo_name": "GITHUB_REPO_NAME",
        "google_spreadsheet_id": "GOOGLE_SPREADSHEET_ID",
    }

    for config_key, env_var in env_mappings.items():
        config_value = project_settings.get(config_key)
        if config_value:  # Config has value, override environment variable
            os.environ[env_var] = str(config_value)

    # Apply log_level from config if specified
    log_level = config.get("log_level")
    if log_level:
        set_log_level(log_level)
        print(f"[INFO] Log level set to: {log_level}")

    return phases, default_assignee, output_dir, project_settings


def load_team_members_from_yaml(config_path: Path, detailed: bool = False):
    """
    Load team members from YAML config file.

    Supports both formats:
    - team_members with 'email' field (for Jira)
    - team_members with 'name' field (for GitHub)

    Args:
        config_path: Path to YAML configuration file
        detailed: If True, return dict with full details (leave_days, capacity)
                  If False, return list of identifiers only

    Returns:
        If detailed=False: List of team member identifiers (emails or usernames)
        If detailed=True: Dict mapping identifier to member details:
            {
                'wlin@redhat.com': {
                    'member': 'wlin',
                    'email': 'wlin@redhat.com',
                    'leave_days': [...],
                    'capacity': 0.8
                },
                ...
            }

    Raises:
        FileNotFoundError: If config file doesn't exist
    """
    if not config_path.exists():
        return {} if detailed else []

    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
    except yaml.YAMLError:
        return {} if detailed else []

    if not config or "team_members" not in config:
        return {} if detailed else []

    if detailed:
        # Return detailed information
        members_details = {}
        for member in config["team_members"]:
            if isinstance(member, dict):
                identifier = member.get("email") or member.get("name")
                if identifier:
                    members_details[identifier] = {
                        "member": member.get("member", identifier),
                        "email": member.get("email"),
                        "name": member.get("name"),
                        "leave_days": member.get("leave_days") or [],
                        "capacity": member.get("capacity", 1.0),
                    }
        return members_details
    else:
        # Return simple list (backward compatible)
        members = []
        for member in config["team_members"]:
            if isinstance(member, dict):
                # Support both 'email' (Jira) and 'name' (GitHub)
                # For PR config: prioritize 'name' (GitHub username) over 'email'
                # For Jira config: prioritize 'email' over 'name'
                if "name" in member:
                    # GitHub config: use 'name' (GitHub username) for API queries
                    members.append(member["name"])
                elif "email" in member:
                    # Jira config: use 'email' for API queries
                    members.append(member["email"])
            elif isinstance(member, str):
                members.append(member)
        return members


def cleanup_old_reports(reports_dir: Path, identifier: str, report_type: str) -> None:
    """
    Clean up old report files for a given identifier.

    Args:
        reports_dir: Directory containing reports
        identifier: User identifier or "general"
        report_type: "jira" or "pr"
    """
    reports_dir.mkdir(parents=True, exist_ok=True)

    if report_type == "pr":
        patterns = [
            f"pr_metrics_{identifier}_*.json",
            f"pr_report_{identifier}_*.txt",
            f"pr_comparison_{identifier}_*.tsv",
        ]
        # Also clean combined reports for the "general" identifier (team report)
        if identifier == "general":
            patterns.append(f"combined_pr_report_*.tsv")
    elif report_type == "jira":
        patterns = [
            f"jira_metrics_{identifier}_*.json",
            f"jira_report_{identifier}_*.txt",
            f"jira_comparison_{identifier}_*.tsv",
        ]
        # Also clean combined reports for the "general" identifier (team report)
        if identifier == "general":
            patterns.append(f"combined_jira_report_*.tsv")
    else:
        raise ValueError(f"Unknown report type: {report_type}")

    removed_count = 0
    for pattern in patterns:
        for file_path in reports_dir.glob(pattern):
            file_path.unlink()
            removed_count += 1

    print(f"{Colors.GREEN}  ✓ Removed {removed_count} old report files for {identifier}{Colors.NC}")


def extract_sheet_prefix(config_path: Optional[Path]) -> str:
    """
    Extract Google Sheets prefix from config path for complex scenarios.

    Returns the top-level directory name under config/ if it's a complex scenario
    (has subdirectories). For simple scenarios, returns empty string.

    Examples:
        Simple scenarios (return ""):
            config/konfluxui/jira_report_config.yaml → ""

        Complex scenarios (return top-level dir):
            config/cue/cue-konfluxui/jira_report_config.yaml → "cue"
            config/cue/cue-rhtapui/jira_report_config.yaml → "cue"
            config/cue/aggregation_config.yaml → "cue"

    Args:
        config_path: Path to config file or directory

    Returns:
        Sheet prefix string for complex scenarios, or empty string for simple scenarios
    """
    if not config_path:
        return ""

    # Convert to Path if string
    if isinstance(config_path, str):
        config_path = Path(config_path)

    # Get absolute path and resolve
    config_path = config_path.resolve()

    # Find 'config' in path
    parts = config_path.parts
    try:
        config_index = parts.index("config")

        # Check if this is a complex scenario (has subdirectories or aggregation)
        # Simple: config/{team}/file.yaml (config + 2 elements)
        # Complex: config/{top-level}/{sub-project}/file.yaml (config + 3+ elements)
        # Aggregation: config/{top-level}/aggregation_config.yaml (config + 2 elements, but has aggregation_config.yaml)

        # Count elements after 'config'
        elements_after_config = len(parts) - config_index - 1

        # Check if it's an aggregation config
        is_aggregation = parts[-1] == "aggregation_config.yaml"

        # If there are 3+ elements after 'config', OR it's an aggregation config, it's complex
        if elements_after_config >= 3 or (elements_after_config == 2 and is_aggregation):
            # Return the top-level directory (first dir after config/)
            return parts[config_index + 1]

    except (ValueError, IndexError):
        pass

    return ""


def upload_to_google_sheets(
    report_file: Optional[Path],
    skip_upload: bool = False,
    show_manual_instructions: bool = True,
    config_path: Optional[Path] = None,
) -> bool:
    """
    Upload report to Google Sheets if configured.

    Args:
        report_file: Path to report file to upload
        skip_upload: If True, skip upload and only show manual instructions (default: False)
        show_manual_instructions: If True, show manual upload instructions when needed (default: True)
        config_path: Path to config file/directory (used to extract sheet prefix)

    Returns:
        True if upload succeeded or was skipped, False if upload failed

    Example:
        # Auto-upload (default behavior)
        upload_to_google_sheets(report_file, config_path=config_path)

        # Skip upload with instructions
        upload_to_google_sheets(report_file, skip_upload=True)

        # Skip upload silently
        upload_to_google_sheets(report_file, skip_upload=True, show_manual_instructions=False)
    """
    if not report_file or not report_file.exists():
        return False

    # Skip upload if requested
    if skip_upload:
        if show_manual_instructions:
            print(f"{Colors.BLUE}⏭️  Skipping upload (--no-upload specified){Colors.NC}")
            print()
            print("📤 To upload later:")
            print(f"  python3 -m impactlens.scripts.upload_to_sheets --report {report_file}")
            print()
        return True

    credentials = os.getenv("GOOGLE_CREDENTIALS_FILE")
    spreadsheet_id = os.getenv("GOOGLE_SPREADSHEET_ID")

    if credentials and spreadsheet_id:
        print(f"{Colors.YELLOW}📤 Uploading to Google Sheets...{Colors.NC}")

        # Build command with --config if provided
        cmd = [
            sys.executable,
            "-m",
            "impactlens.scripts.upload_to_sheets",
            "--report",
            str(report_file),
        ]

        # Add --config parameter if config_path is provided
        if config_path:
            cmd.extend(["--config", str(config_path)])

        try:
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
            )
            # Print stdout from upload script
            if result.stdout:
                print(result.stdout, end="")
            print(f"{Colors.GREEN}   ✓ Upload successful{Colors.NC}")
            print()
            return True
        except subprocess.CalledProcessError as e:
            print(f"{Colors.RED}   ⚠ Upload failed: {e}{Colors.NC}")
            # Print stderr to show actual error details
            if e.stderr:
                print(f"{Colors.RED}   Error details (stderr):{Colors.NC}")
                print(e.stderr)
            # Also print stdout in case error is there
            if e.stdout:
                print(f"{Colors.RED}   Output (stdout):{Colors.NC}")
                print(e.stdout)
            if not e.stderr and not e.stdout:
                print(
                    f"{Colors.RED}   No error output captured. Exit code: {e.returncode}{Colors.NC}"
                )
            if show_manual_instructions:
                print("   You can upload manually:")
                print(f"   python3 -m impactlens.scripts.upload_to_sheets --report {report_file}")
            print()
            return False
    else:
        if show_manual_instructions:
            print(f"{Colors.BLUE}Google Sheets upload not configured (optional){Colors.NC}")
            print(
                "You can open this file in Google Sheets manually, or configure automatic upload:"
            )
            print("  export GOOGLE_CREDENTIALS_FILE=/path/to/credentials.json")
            print("  export GOOGLE_SPREADSHEET_ID=your_spreadsheet_id")
            print()
            print("Or upload manually:")
            print(f"  python3 -m impactlens.scripts.upload_to_sheets --report {report_file}")
            print()
        return False


def find_latest_comparison_report(
    reports_dir: Path, identifier: str, report_type: str
) -> Optional[Path]:
    """
    Find the most recent comparison report.

    Args:
        reports_dir: Directory containing reports
        identifier: User identifier or "general"
        report_type: "jira" or "pr"

    Returns:
        Path to latest report or None
    """
    if report_type == "jira":
        pattern = f"jira_comparison_{identifier}_*.tsv"
    elif report_type == "pr":
        pattern = f"pr_comparison_{identifier}_*.tsv"
    else:
        return None

    files = list(reports_dir.glob(pattern))
    if not files:
        return None

    # Sort by modification time, newest first
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0]


def load_team_members(team_members_file: Path) -> List[str]:
    """
    Load team members from YAML configuration file.

    Args:
        team_members_file: Path to YAML team members config

    Returns:
        List of team member emails
    """
    return load_team_members_from_yaml(team_members_file)


def resolve_member_identifier(
    identifier: str, config_path: Path
) -> Tuple[Optional[str], Optional[Dict]]:
    """
    Resolve member identifier to email and details.

    Supports both short format (e.g., "wlin") and email format (e.g., "wlin@redhat.com").
    If short format is provided, looks up the member in team_members config.

    Args:
        identifier: Member identifier (short name or email)
        config_path: Path to YAML configuration file

    Returns:
        Tuple of (email, member_details) or (None, None) if not found
    """
    if not identifier:
        return None, None

    # Load all team members with details
    members_details = load_team_members_from_yaml(config_path, detailed=True)

    # Check if identifier is already an email in our config
    if identifier in members_details:
        return identifier, members_details[identifier]

    # Otherwise, try to find by short member name
    for email, details in members_details.items():
        member_name = details.get("member", "")
        if member_name == identifier:
            return email, details

    # Not found, return identifier as-is (for backward compatibility)
    return identifier, None


def run_report_for_member(
    script_path: Path, member: str, report_type: str, extra_args: Optional[List[str]] = None
) -> bool:
    """
    Run report generation for a single team member.

    Args:
        script_path: Path to this script (for recursive calls)
        member: Team member identifier
        report_type: "jira" or "pr"
        extra_args: Additional arguments to pass

    Returns:
        True if successful, False otherwise
    """
    args = [sys.executable, "-m"]

    if report_type == "jira":
        args.extend(["impactlens.cli.generate_jira_report", member])
    elif report_type == "pr":
        args.extend(["impactlens.cli.generate_pr_report", member])
    else:
        return False

    if extra_args:
        args.extend(extra_args)

    try:
        subprocess.run(args, check=True)
        return True
    except subprocess.CalledProcessError:
        print(f"{Colors.RED}  ✗ Failed to generate report for {member}{Colors.NC}")
        return False
