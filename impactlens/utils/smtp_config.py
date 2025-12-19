"""
SMTP Configuration Utilities.

Centralize SMTP configuration reading and EmailNotifier creation
to avoid code duplication across the codebase.
"""

import os
from typing import Optional, Dict, Any, TYPE_CHECKING
from pathlib import Path

if TYPE_CHECKING:
    from impactlens.utils.email_notifier import EmailNotifier


def get_smtp_config() -> Dict[str, Any]:
    """
    Get SMTP configuration from environment variables.

    Returns a dictionary with SMTP settings, using Gmail defaults
    if specific values are not provided.

    For CI: Uses MAIL_APP_USER and MAIL_APP_PASSWORD (GitHub Secrets)
    For local: Uses SMTP_USER and SMTP_PASSWORD (or environment variables)

    Returns:
        Dict with keys: smtp_host, smtp_port, smtp_user, smtp_password, from_email
        Returns None values if SMTP is not configured.
    """
    # Check both local and CI secret names (with priority to SMTP_* for local dev)
    smtp_user = os.getenv("SMTP_USER") or os.getenv("MAIL_APP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD") or os.getenv("MAIL_APP_PASSWORD")

    # SMTP server settings with Gmail defaults
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))

    # From email with display name
    from_email_env = os.getenv("FROM_EMAIL")
    from_email = (
        from_email_env if from_email_env else (f"ImpactLens <{smtp_user}>" if smtp_user else None)
    )

    return {
        "smtp_host": smtp_host,
        "smtp_port": smtp_port,
        "smtp_user": smtp_user,
        "smtp_password": smtp_password,
        "from_email": from_email,
    }


def create_email_notifier(smtp_config: Optional[Dict[str, Any]] = None) -> "EmailNotifier":
    """
    Create an EmailNotifier instance with SMTP configuration.

    Args:
        smtp_config: Optional SMTP configuration dict. If None, will call get_smtp_config()

    Returns:
        EmailNotifier instance configured with SMTP settings
    """
    from impactlens.utils.email_notifier import EmailNotifier

    if smtp_config is None:
        smtp_config = get_smtp_config()

    return EmailNotifier(
        smtp_host=smtp_config["smtp_host"],
        smtp_port=smtp_config["smtp_port"],
        smtp_user=smtp_config["smtp_user"],
        smtp_password=smtp_config["smtp_password"],
        from_email=smtp_config["from_email"],
    )


def is_smtp_configured() -> bool:
    """
    Check if SMTP is configured with at least the minimum required settings.

    Returns:
        True if SMTP_HOST (or default Gmail) is available, False otherwise
    """
    smtp_config = get_smtp_config()
    return bool(smtp_config["smtp_host"])


def print_smtp_config_summary(config: Optional[Dict[str, Any]] = None) -> None:
    """
    Print a summary of SMTP configuration (for debugging/logging).

    Args:
        config: Optional SMTP config dict. If None, will call get_smtp_config()
    """
    if config is None:
        config = get_smtp_config()

    print(f"SMTP Configuration:")
    print(f"  Host: {config['smtp_host'] or 'Not configured'}")
    print(f"  Port: {config['smtp_port'] or 'Not configured'}")
    print(f"  From: {config['from_email'] or 'Not configured'}")
    print(f"  User: {'***' if config['smtp_user'] else 'Not configured'}")
    print(f"  Password: {'***' if config['smtp_password'] else 'Not configured'}")
    print()


def send_email_notifications_cli(
    config_file_path: Optional[Path],
    report_context: str,
    console: Optional[Any] = None,
    test_mode: bool = False,
) -> None:
    """
    Send email notifications to team members from CLI workflow.

    This is a convenience function for CLI commands to send email notifications
    without duplicating the same code across jira full, pr full, and full commands.

    Args:
        config_file_path: Path to config file (jira_report_config.yaml or pr_report_config.yaml)
                          Can be Path object or string
        report_context: Context message for the email (e.g., "Jira Report Generated")
        console: Optional Rich console for formatted output
        test_mode: If True, only send emails to wlin@redhat.com (for testing)
    """
    try:
        from impactlens.utils.email_notifier import notify_team_members
        from impactlens.utils.anonymization import _global_anonymizer
        from impactlens.utils.workflow_utils import load_team_members_from_yaml
        import os

        # Load team members from config
        if config_file_path:
            # Convert to Path if string (load_team_members_from_yaml expects Path object)
            if isinstance(config_file_path, str):
                config_file_path = Path(config_file_path)

            # Load detailed team member info (returns dict)
            team_members_dict = load_team_members_from_yaml(config_file_path, detailed=True)
            # Convert dict to list of dicts for notify_team_members
            team_members = list(team_members_dict.values()) if team_members_dict else []

            # Pre-populate anonymizer with all team member names
            # This ensures everyone gets a consistent anonymous ID
            for member in team_members:
                name = member.get("member") or member.get("name")
                if name:
                    _global_anonymizer.anonymize(name)

            # Test mode: filter to only wlin@redhat.com
            if test_mode:
                original_count = len(team_members)
                team_members = [m for m in team_members if m.get("email") == "wlin@redhat.com"]
                if console and original_count > 0:
                    console.print(
                        f"[yellow]🧪 TEST MODE: Filtered {original_count} members to {len(team_members)} "
                        f"(only wlin@redhat.com)[/yellow]"
                    )
                if not team_members and console:
                    console.print(
                        "[yellow]⚠️  No test email (wlin@redhat.com) found in team members[/yellow]"
                    )
                    return

            # Get PR URL from environment (if in CI)
            pr_url = os.getenv("GITHUB_PR_URL")

            # Check if we're in dry-run mode (missing SMTP config)
            dry_run = not is_smtp_configured()

            if dry_run and console:
                console.print("[yellow]ℹ️  SMTP not configured - running in dry-run mode[/yellow]")

            # Send notifications
            results = notify_team_members(
                anonymizer=_global_anonymizer,
                team_members=team_members,
                pr_url=pr_url,
                report_context=report_context,
                dry_run=dry_run,
            )

            success_count = sum(1 for v in results.values() if v)
            if console:
                console.print(
                    f"[green]✓ Email notifications: {success_count}/{len(results)} sent[/green]"
                )
        else:
            if console:
                console.print(
                    "[yellow]⚠️  No config file specified - cannot load team members[/yellow]"
                )

    except Exception as e:
        if console:
            console.print(f"[red]✗ Error sending email notifications: {e}[/red]")
            console.print("[yellow]   Continuing with workflow...[/yellow]")
