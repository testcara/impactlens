#!/usr/bin/env python3
"""
ImpactLens - Unified CLI Interface.

This module provides a unified command-line interface for all ImpactLens operations.
It uses clear subcommands to avoid ambiguity and ensure consistent behavior.
"""

import sys
import subprocess
from pathlib import Path
from typing import Optional

import typer
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from impactlens.utils.logger import set_log_level
from impactlens.core.report_aggregator import ReportAggregator
from impactlens.utils.workflow_utils import upload_to_google_sheets
from impactlens.utils.smtp_config import send_email_notifications_cli

# Main app
app = typer.Typer(
    name="impactlens",
    help="ImpactLens - Measure the impact of AI tools on development efficiency as well as team and individual performance",
    add_completion=False,
)

# Subcommands for Jira and PR
jira_app = typer.Typer(help="Jira issue analysis commands")
pr_app = typer.Typer(help="GitHub PR analysis commands")

app.add_typer(jira_app, name="jira")
app.add_typer(pr_app, name="pr")

console = Console()


def _resolve_single_config(config_path: Path, config_filename: str) -> Path:
    """
    Internal helper: resolve a single config file path.

    Args:
        config_path: Path object (directory or file)
        config_filename: Config filename to look for if directory

    Returns:
        Resolved config file path
    """
    if config_path.is_dir():
        return config_path / config_filename
    else:
        return config_path


def _add_visualization_link_to_report(report_path: str, visualization_link: str) -> None:
    """
    Add visualization link to an existing combined report.

    Updates the report in-place by inserting the visualization link
    after the description text.

    Args:
        report_path: Path to the combined report TSV file
        visualization_link: Github png link for attaching sheets
    """
    with open(report_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Find the insertion point (after the description, before phase info)
    insert_index = None
    for i, line in enumerate(lines):
        # Look for the line that ends the description section
        # (the empty line before "Phase 1:" or before "Visualization Report:")
        if i + 1 < len(lines) and lines[i].strip() == "" and lines[i + 1].startswith("Phase 1:"):
            insert_index = i
            break
        # Skip if link already exists
        if line.startswith("Visualization Report:"):
            return  # Already has visualization link

    if insert_index is not None:
        # Insert visualization link
        lines.insert(insert_index, f"Visualization Report: {visualization_link}\n")
        lines.insert(insert_index + 1, "\n")

        # Write back
        with open(report_path, "w", encoding="utf-8") as f:
            f.writelines(lines)


def resolve_config_path(
    config: Optional[str], config_filename: str, color: str = "cyan"
) -> Optional[Path]:
    """
    Resolve config path - handles both directory and file paths.

    Args:
        config: Config path (directory or file) provided by user
        config_filename: Config filename to look for if directory is provided
        color: Color for console output (cyan, magenta, etc.)

    Returns:
        Resolved config file path, or None if config is None
    """
    if not config:
        return None

    config_path = Path(config)
    resolved_path = _resolve_single_config(config_path, config_filename)

    if config_path.is_dir():
        console.print(f"[{color}]Using config directory: {config}[/{color}]")
        console.print(f"  - Config file: {resolved_path}")
    else:
        console.print(f"[{color}]Using config file: {config}[/{color}]")

    return resolved_path


def should_send_email_notification(
    email_anonymous_id_flag: bool,
    config_file_path: Optional[Path],
) -> bool:
    """
    Determine if email notifications should be sent.

    Priority:
    1. If --email-anonymous-id flag is explicitly provided, use it (True)
    2. Otherwise, check config file's email_anonymous_id.enabled setting
    3. Default to False if config not found or no setting

    Args:
        email_anonymous_id_flag: Value of the --email-anonymous-id CLI flag
        config_file_path: Path to the config file

    Returns:
        True if emails should be sent, False otherwise
    """
    # If flag is explicitly set, use it
    if email_anonymous_id_flag:
        console.print(
            "[bold green]✓[/bold green] Email notification enabled via --email-anonymous-id flag"
        )
        return True

    # Otherwise, check config file
    if not config_file_path:
        console.print("[dim]No config file provided - email notifications disabled[/dim]")
        return False

    try:
        from impactlens.utils.workflow_utils import load_config_file

        _, root_configs = load_config_file(config_file_path)
        email_enabled = root_configs.get("email_anonymous_id", False)
        if email_enabled:
            console.print("[bold green]✓[/bold green] Email notifications enabled in config")
        else:
            console.print(
                "[dim]Email notifications disabled in config (email_anonymous_id: false)[/dim]"
            )

        return email_enabled
    except Exception as e:
        console.print(f"[dim]Failed to read email config: {e} - notifications disabled[/dim]")
        return False


def resolve_config_paths_for_full(
    config: Optional[str],
) -> tuple[Optional[Path], Optional[Path]]:
    """
    Resolve both jira and pr config paths for full workflow.

    Args:
        config: Config path (directory or file) provided by user

    Returns:
        Tuple of (jira_config_path, pr_config_path)
    """
    if not config:
        return None, None

    config_path = Path(config)
    jira_config = _resolve_single_config(config_path, "jira_report_config.yaml")
    pr_config = _resolve_single_config(config_path, "pr_report_config.yaml")

    if config_path.is_dir():
        console.print(
            f"[cyan]Using config directory: {config}[/cyan]\n"
            f"  - Jira config: {jira_config}\n"
            f"  - PR config: {pr_config}"
        )
    else:
        console.print(f"[cyan]Using config file: {config}[/cyan]")

    return jira_config, pr_config


def generate_visualization_for_report(
    config_file_path: Optional[Path],
    no_visualization: bool,
    no_upload: bool,
    report_type: str,
    failed_steps: list,
) -> None:
    """
    Generate visualizations for combined reports (Jira or PR).

    Priority:
    1. If --no-visualization flag is set, skip visualization
    2. Otherwise, check config file's visualization.enabled setting
    3. Default to True if config not found or no setting

    Args:
        config_file_path: Path to the config file
        no_visualization: Value of the --no-visualization CLI flag
        no_upload: Value of the --no-upload CLI flag (controls chart upload)
        report_type: "jira" or "pr"
        failed_steps: List to append failure messages to
    """
    # Load config and set environment variables (needed for sheet naming)
    if config_file_path:
        try:
            from impactlens.utils.workflow_utils import (
                load_config_file,
                apply_project_settings_to_env,
            )

            # Load config to get project settings (jira_project_key, github_repo_name, etc.)
            project_settings, root_configs = load_config_file(config_file_path)

            # Apply project settings to environment variables (already done in load_config_file)
            # apply_project_settings_to_env(project_settings)

            # Get replace_existing setting from config
            replace_existing = root_configs.get("replace_existing_reports", False)
        except Exception as e:
            print(f"⚠️  Warning: Failed to load config for visualization: {e}")
            replace_existing = False

    # Initialize replace_existing if not set
    if "replace_existing" not in locals():
        replace_existing = False

    # Check if visualization should be enabled
    should_generate_visualization = not no_visualization

    # Check config file for visualization.enabled setting (CLI param takes priority)
    if not no_visualization and config_file_path and "root_configs" in locals():
        try:
            # Use root_configs from earlier load_config_file call
            config_enabled = root_configs.get("visualization", True)  # Default to True
            should_generate_visualization = config_enabled
        except Exception:
            pass  # If config read fails, keep CLI behavior

    if should_generate_visualization:
        console.print("\n[bold]Step 2.8/3:[/bold] Generating visualizations...")
        from impactlens.utils.visualization import generate_charts_from_combined_report

        # Find latest combined report based on type
        if report_type == "jira":
            report_pattern = "**/combined_jira_report_*.tsv"
            report_type_label = "Jira"
        else:  # pr
            report_pattern = "**/combined_pr_report_*.tsv"
            report_type_label = "PR"

        combined_reports = list(Path("reports").glob(report_pattern))
        if combined_reports:
            latest_combined = max(combined_reports, key=lambda p: p.stat().st_mtime)
            charts_dir = latest_combined.parent / "charts"

            try:
                import os

                # Check if Google Sheets is configured
                has_sheets = bool(os.environ.get("GOOGLE_SPREADSHEET_ID"))

                generated_charts, result_info = generate_charts_from_combined_report(
                    report_path=str(latest_combined),
                    output_dir=str(charts_dir),
                    upload_charts_to_github=not no_upload,  # Upload PNG charts to GitHub (unless --no-upload)
                    create_sheets_visualization=has_sheets,  # Create Google Sheets visualization
                    spreadsheet_id=os.environ.get("GOOGLE_SPREADSHEET_ID"),
                    config_path=str(config_file_path) if config_file_path else None,
                    replace_existing=replace_existing,  # Delete old sheets if enabled in config
                )

                if generated_charts:
                    console.print(f"[green]✓[/green] Generated {len(generated_charts)} charts")

                    if result_info:
                        # Show GitHub upload results
                        if result_info.get("chart_github_links"):
                            num_uploaded = len(result_info["chart_github_links"])
                            console.print(
                                f"[green]✓[/green] Uploaded {num_uploaded} charts to GitHub"
                            )

                        # Show Sheets visualization results
                        if result_info.get("sheet_info"):
                            sheet_info = result_info["sheet_info"]
                            console.print(
                                f"[green]✓[/green] Created visualization sheet: {sheet_info['sheet_name']}"
                            )
                            console.print(f"[green]✓[/green] Sheets URL: {sheet_info['url']}")

                            # Update combined report with visualization link
                            try:
                                _add_visualization_link_to_report(
                                    str(latest_combined), sheet_info["url"]
                                )
                                console.print(
                                    f"[green]✓[/green] Updated combined report with visualization link"
                                )
                            except Exception as e:
                                console.print(
                                    f"[yellow]⚠[/yellow] Failed to update combined report: {e}"
                                )
                else:
                    console.print("[yellow]⚠[/yellow] No charts generated")
            except Exception as e:
                console.print(f"[yellow]⚠[/yellow] Visualization failed: {e}")
                failed_steps.append(f"{report_type_label} visualizations")
        else:
            console.print(
                f"[yellow]ℹ️  No combined {report_type_label} reports found, skipping visualizations[/yellow]"
            )
    else:
        console.print(
            "\n[bold yellow]ℹ️  Visualization skipped[/bold yellow] (disabled via --no-visualization or config)"
        )


def run_script(script_path: str, args: list[str], description: str) -> int:
    """Run a Python script and display progress."""
    cmd = [sys.executable, "-m", script_path] + args

    console.print(f"[bold blue]→[/bold blue] {description}")

    result = subprocess.run(cmd, capture_output=False)

    if result.returncode == 0:
        console.print(f"[bold green]✓[/bold green] {description} - Done\n")
    else:
        console.print(f"[bold red]✗[/bold red] {description} - Failed\n")

    return result.returncode


# ============================================================================
# Jira Commands
# ============================================================================


@jira_app.command(name="team")
def jira_team(
    config: Optional[str] = typer.Option(None, "--config", help="Custom config file path"),
    no_upload: bool = typer.Option(False, "--no-upload", help="Skip uploading to Google Sheets"),
):
    """Generate Jira report for TEAM OVERALL only."""
    console.print(
        Panel.fit(
            "[bold cyan]Jira Team Report[/bold cyan]\n"
            "[dim]Generating report for the entire team[/dim]",
            border_style="cyan",
        )
    )

    args = []
    if config:
        args.extend(["--config", config])
    if no_upload:
        args.append("--no-upload")

    script = "impactlens.scripts.generate_jira_report"
    return_code = run_script(script, args, "Generating Jira team report")
    sys.exit(return_code)


@jira_app.command(name="member")
def jira_member(
    email: str = typer.Argument(..., help="Team member email (e.g., user@example.com)"),
    config: Optional[str] = typer.Option(None, "--config", help="Custom config file path"),
    no_upload: bool = typer.Option(False, "--no-upload", help="Skip uploading to Google Sheets"),
):
    """Generate Jira report for a SINGLE team member."""
    console.print(
        Panel.fit(
            f"[bold cyan]Jira Individual Report[/bold cyan]\n" f"[dim]Member: {email}[/dim]",
            border_style="cyan",
        )
    )

    args = [email]
    if config:
        args.extend(["--config", config])
    if no_upload:
        args.append("--no-upload")

    script = "impactlens.scripts.generate_jira_report"
    return_code = run_script(script, args, f"Generating Jira report for {email}")
    sys.exit(return_code)


@jira_app.command(name="members")
def jira_members(
    config: Optional[str] = typer.Option(None, "--config", help="Custom config file path"),
    no_upload: bool = typer.Option(False, "--no-upload", help="Skip uploading to Google Sheets"),
):
    """Generate Jira reports for ALL individual team members (excludes team report)."""
    console.print(
        Panel.fit(
            "[bold cyan]Jira Members Reports[/bold cyan]\n"
            "[dim]Generating reports for all team members (team report excluded)[/dim]",
            border_style="cyan",
        )
    )

    # Note: We need to manually iterate through members here
    # For now, using --all-members but this should be refactored
    args = ["--all-members"]
    if config:
        args.extend(["--config", config])
    if no_upload:
        args.append("--no-upload")

    script = "impactlens.scripts.generate_jira_report"
    return_code = run_script(script, args, "Generating Jira reports for all members")

    console.print(
        "\n[yellow]Note:[/yellow] This currently includes team report. "
        "Use 'jira all' for explicit team + members generation."
    )
    sys.exit(return_code)


@jira_app.command(name="all")
def jira_all(
    config: Optional[str] = typer.Option(None, "--config", help="Custom config file path"),
    no_upload: bool = typer.Option(False, "--no-upload", help="Skip uploading to Google Sheets"),
):
    """Generate Jira reports for TEAM + ALL MEMBERS."""
    console.print(
        Panel.fit(
            "[bold cyan]Jira Complete Reports[/bold cyan]\n"
            "[dim]Generating team report + all individual member reports[/dim]",
            border_style="cyan",
        )
    )

    args = ["--all-members"]
    if config:
        args.extend(["--config", config])
    if no_upload:
        args.append("--no-upload")

    script = "impactlens.scripts.generate_jira_report"
    return_code = run_script(script, args, "Generating Jira team + members reports")
    sys.exit(return_code)


@jira_app.command(name="combine")
def jira_combine(
    config: Optional[str] = typer.Option(None, "--config", help="Custom config file path"),
    no_upload: bool = typer.Option(False, "--no-upload", help="Skip uploading to Google Sheets"),
):
    """COMBINE existing Jira reports without regenerating."""
    console.print(
        Panel.fit(
            "[bold cyan]Combine Jira Reports[/bold cyan]\n"
            "[dim]Combining existing reports into a single TSV file[/dim]",
            border_style="cyan",
        )
    )

    args = ["--combine-only"]
    if config:
        args.extend(["--config", config])
    if no_upload:
        args.append("--no-upload")

    script = "impactlens.scripts.generate_jira_report"
    return_code = run_script(script, args, "Combining Jira reports")
    sys.exit(return_code)


def _jira_full_impl(
    config: Optional[str],
    no_upload: bool,
    upload_members: bool,
    hide_individual_names: bool,
    email_anonymous_id: bool,
    mail_save_file: Optional[str],
    with_claude_insights: bool,
    claude_api_mode: bool,
    no_visualization: bool,
    skip_email: bool = False,
) -> int:
    """
    Internal implementation of Jira full workflow.

    Args:
        skip_email: If True, skip sending email notifications (used in full_workflow)

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    workflow_steps = "Team → Members → Combine → Upload"
    if with_claude_insights:
        workflow_steps = "Team → Members → Combine → Claude Insights → Upload"

    console.print(
        Panel.fit(
            "[bold cyan]Full Jira Workflow[/bold cyan]\n" f"[dim]{workflow_steps}[/dim]",
            border_style="cyan",
        )
    )

    # Resolve config path (directory or specific file)
    config_file_path = resolve_config_path(config, "jira_report_config.yaml", "cyan")

    failed_steps = []

    # Step 1: Generate team + all members
    console.print("\n[bold]Step 1/3:[/bold] Generating team + members reports...")
    args = ["--all-members"]
    if config_file_path:
        args.extend(["--config", str(config_file_path)])
    if no_upload:
        args.append("--no-upload")
    if upload_members:
        args.append("--upload-members")
    if hide_individual_names:
        args.append("--hide-individual-names")

    if run_script("impactlens.scripts.generate_jira_report", args, "Jira all reports") != 0:
        failed_steps.append("Jira all reports")

    # Step 2: Combine reports
    console.print("\n[bold]Step 2/3:[/bold] Combining reports...")
    args = ["--combine-only"]
    if config_file_path:
        args.extend(["--config", str(config_file_path)])
    if no_upload:
        args.append("--no-upload")
    if hide_individual_names:
        args.append("--hide-individual-names")

    if run_script("impactlens.scripts.generate_jira_report", args, "Jira combine") != 0:
        failed_steps.append("Jira combine")

    # Step 2.5: Email Notifications (opt-in, only with anonymization)
    if not skip_email and should_send_email_notification(email_anonymous_id, config_file_path):
        if not hide_individual_names:
            console.print(
                "\n[bold yellow]⚠️  --email-anonymous-id requires --hide-individual-names[/bold yellow]"
            )
            console.print("[yellow]   Email notifications skipped.[/yellow]")
        else:
            console.print("\n[bold]Step 2.5/3:[/bold] Sending email notifications...")

            send_email_notifications_cli(
                config_file_path=config_file_path,
                report_context="Jira Report Generated",
                console=console,
                mail_save_file=mail_save_file,
            )

    # Step 2.8: Generate Visualizations
    generate_visualization_for_report(
        config_file_path=config_file_path,
        no_visualization=no_visualization,
        no_upload=no_upload,
        report_type="jira",
        failed_steps=failed_steps,
    )

    # Step 3: Claude Insights (opt-in)
    if with_claude_insights:
        console.print("\n[bold]Step 3/3:[/bold] Generating Claude insights...")
        jira_reports = list(Path("reports/jira").glob("combined_jira_report_*.tsv"))
        if jira_reports:
            latest_jira = max(jira_reports, key=lambda p: p.stat().st_mtime)

            # Build args for analyze script
            analyze_args = ["--report", str(latest_jira)]
            if no_upload:
                analyze_args.append("--no-upload")
            if claude_api_mode:
                analyze_args.append("--claude-api-mode")

            if (
                run_script(
                    "impactlens.scripts.analyze_with_claude_code",
                    analyze_args,
                    f"Claude insights: {latest_jira.name}",
                )
                != 0
            ):
                failed_steps.append("Jira Claude insights")
    else:
        console.print(
            "\n[bold yellow]ℹ️  Claude insights skipped[/bold yellow] (use --with-claude-insights to enable)"
        )

    # Summary
    console.print("\n" + "=" * 60)
    if failed_steps:
        console.print(
            f"[bold yellow]⚠ Workflow completed with {len(failed_steps)} failures:[/bold yellow]"
        )
        for step in failed_steps:
            console.print(f"  [red]✗[/red] {step}")
        return 1
    else:
        console.print("[bold green]✓ Jira full workflow completed successfully![/bold green]")
        return 0


@jira_app.command(name="full")
def jira_full(
    config: Optional[str] = typer.Option(
        None,
        "--config",
        help="Config file path or directory (e.g., config/team-a/jira_report_config.yaml or config/team-a)",
    ),
    no_upload: bool = typer.Option(False, "--no-upload", help="Skip uploading to Google Sheets"),
    upload_members: bool = typer.Option(
        False,
        "--upload-members",
        help="Upload individual member reports (default: only team/combined)",
    ),
    hide_individual_names: bool = typer.Option(
        False,
        "--hide-individual-names",
        help="Anonymize individual names in combined reports and hide sensitive fields",
    ),
    email_anonymous_id: bool = typer.Option(
        False,
        "--email-anonymous-id",
        help="Email each member ONLY their own anonymous ID (requires --hide-individual-names)",
    ),
    mail_save_file: Optional[str] = typer.Option(
        None,
        "--mail-save-file",
        help="Save emails to files instead of sending them (specify directory path)",
    ),
    with_claude_insights: bool = typer.Option(
        False, "--with-claude-insights", help="Generate insights using Claude Code (requires setup)"
    ),
    claude_api_mode: bool = typer.Option(
        False,
        "--claude-api-mode",
        help="Use Anthropic API instead of Claude Code CLI (requires ANTHROPIC_API_KEY)",
    ),
    no_visualization: bool = typer.Option(
        False,
        "--no-visualization",
        help="Skip generating charts and HTML visualization report",
    ),
):
    """
    Complete Jira workflow: generate all reports and combine.

    Workflow: Team → Members → Combine → Upload (Claude insights optional with --with-claude-insights)

    Config parameter:
    - Directory: config/team-a (auto-finds jira_report_config.yaml)
    - Specific file: config/team-a/jira_report_config.yaml
    """
    exit_code = _jira_full_impl(
        config=config,
        no_upload=no_upload,
        upload_members=upload_members,
        hide_individual_names=hide_individual_names,
        email_anonymous_id=email_anonymous_id,
        mail_save_file=mail_save_file,
        with_claude_insights=with_claude_insights,
        claude_api_mode=claude_api_mode,
        no_visualization=no_visualization,
    )
    sys.exit(exit_code)


# ============================================================================
# PR Commands
# ============================================================================


@pr_app.command(name="team")
def pr_team(
    config: Optional[str] = typer.Option(None, "--config", help="Custom config file path"),
    incremental: bool = typer.Option(False, "--incremental", help="Only fetch new/updated PRs"),
    no_upload: bool = typer.Option(False, "--no-upload", help="Skip uploading to Google Sheets"),
):
    """Generate PR report for TEAM OVERALL only."""
    console.print(
        Panel.fit(
            "[bold magenta]PR Team Report[/bold magenta]\n"
            "[dim]Generating report for the entire team[/dim]",
            border_style="magenta",
        )
    )

    args = []
    if config:
        args.extend(["--config", config])
    if incremental:
        args.append("--incremental")
    if no_upload:
        args.append("--no-upload")

    script = "impactlens.scripts.generate_pr_report"
    return_code = run_script(script, args, "Generating PR team report")
    sys.exit(return_code)


@pr_app.command(name="member")
def pr_member(
    username: str = typer.Argument(..., help="GitHub username (e.g., wlin)"),
    config: Optional[str] = typer.Option(None, "--config", help="Custom config file path"),
    incremental: bool = typer.Option(False, "--incremental", help="Only fetch new/updated PRs"),
    no_upload: bool = typer.Option(False, "--no-upload", help="Skip uploading to Google Sheets"),
):
    """Generate PR report for a SINGLE team member."""
    console.print(
        Panel.fit(
            f"[bold magenta]PR Individual Report[/bold magenta]\n" f"[dim]Member: {username}[/dim]",
            border_style="magenta",
        )
    )

    args = [username]
    if config:
        args.extend(["--config", config])
    if incremental:
        args.append("--incremental")
    if no_upload:
        args.append("--no-upload")

    script = "impactlens.scripts.generate_pr_report"
    return_code = run_script(script, args, f"Generating PR report for {username}")
    sys.exit(return_code)


@pr_app.command(name="members")
def pr_members(
    config: Optional[str] = typer.Option(None, "--config", help="Custom config file path"),
    incremental: bool = typer.Option(False, "--incremental", help="Only fetch new/updated PRs"),
    no_upload: bool = typer.Option(False, "--no-upload", help="Skip uploading to Google Sheets"),
):
    """Generate PR reports for ALL individual team members (excludes team report)."""
    console.print(
        Panel.fit(
            "[bold magenta]PR Members Reports[/bold magenta]\n"
            "[dim]Generating reports for all team members (team report excluded)[/dim]",
            border_style="magenta",
        )
    )

    # Note: We need to manually iterate through members here
    # For now, using --all-members but this should be refactored
    args = ["--all-members"]
    if config:
        args.extend(["--config", config])
    if incremental:
        args.append("--incremental")
    if no_upload:
        args.append("--no-upload")

    script = "impactlens.scripts.generate_pr_report"
    return_code = run_script(script, args, "Generating PR reports for all members")

    console.print(
        "\n[yellow]Note:[/yellow] This currently includes team report. "
        "Use 'pr all' for explicit team + members generation."
    )
    sys.exit(return_code)


@pr_app.command(name="all")
def pr_all(
    config: Optional[str] = typer.Option(None, "--config", help="Custom config file path"),
    incremental: bool = typer.Option(False, "--incremental", help="Only fetch new/updated PRs"),
    no_upload: bool = typer.Option(False, "--no-upload", help="Skip uploading to Google Sheets"),
):
    """Generate PR reports for TEAM + ALL MEMBERS."""
    console.print(
        Panel.fit(
            "[bold magenta]PR Complete Reports[/bold magenta]\n"
            "[dim]Generating team report + all individual member reports[/dim]",
            border_style="magenta",
        )
    )

    args = ["--all-members"]
    if config:
        args.extend(["--config", config])
    if incremental:
        args.append("--incremental")
    if no_upload:
        args.append("--no-upload")

    script = "impactlens.scripts.generate_pr_report"
    return_code = run_script(script, args, "Generating PR team + members reports")
    sys.exit(return_code)


@pr_app.command(name="combine")
def pr_combine(
    config: Optional[str] = typer.Option(None, "--config", help="Custom config file path"),
    no_upload: bool = typer.Option(False, "--no-upload", help="Skip uploading to Google Sheets"),
):
    """COMBINE existing PR reports without regenerating."""
    console.print(
        Panel.fit(
            "[bold magenta]Combine PR Reports[/bold magenta]\n"
            "[dim]Combining existing reports into a single TSV file[/dim]",
            border_style="magenta",
        )
    )

    args = ["--combine-only"]
    if config:
        args.extend(["--config", config])
    if no_upload:
        args.append("--no-upload")

    script = "impactlens.scripts.generate_pr_report"
    return_code = run_script(script, args, "Combining PR reports")
    sys.exit(return_code)


def _pr_full_impl(
    config: Optional[str],
    incremental: bool,
    no_upload: bool,
    upload_members: bool,
    hide_individual_names: bool,
    email_anonymous_id: bool,
    mail_save_file: Optional[str],
    with_claude_insights: bool,
    claude_api_mode: bool,
    no_visualization: bool,
    skip_email: bool = False,
) -> int:
    """
    Internal implementation of PR full workflow.

    Args:
        skip_email: If True, skip sending email notifications (used in full_workflow)

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    workflow_steps = "Team → Members → Combine → Upload"
    if with_claude_insights:
        workflow_steps = "Team → Members → Combine → Claude Insights → Upload"

    console.print(
        Panel.fit(
            "[bold magenta]Full PR Workflow[/bold magenta]\n" f"[dim]{workflow_steps}[/dim]",
            border_style="magenta",
        )
    )

    # Resolve config path (directory or specific file)
    config_file_path = resolve_config_path(config, "pr_report_config.yaml", "magenta")

    failed_steps = []

    # Step 1: Generate team + all members
    console.print("\n[bold]Step 1/3:[/bold] Generating team + members reports...")
    args = ["--all-members"]
    if config_file_path:
        args.extend(["--config", str(config_file_path)])
    if incremental:
        args.append("--incremental")
    if no_upload:
        args.append("--no-upload")
    if upload_members:
        args.append("--upload-members")
    if hide_individual_names:
        args.append("--hide-individual-names")

    if run_script("impactlens.scripts.generate_pr_report", args, "PR all reports") != 0:
        failed_steps.append("PR all reports")

    # Step 2: Combine reports
    console.print("\n[bold]Step 2/3:[/bold] Combining reports...")
    args = ["--combine-only"]
    if config_file_path:
        args.extend(["--config", str(config_file_path)])
    if no_upload:
        args.append("--no-upload")
    if hide_individual_names:
        args.append("--hide-individual-names")

    if run_script("impactlens.scripts.generate_pr_report", args, "PR combine") != 0:
        failed_steps.append("PR combine")

    # Step 2.5: Email Notifications (opt-in, only with anonymization)
    if not skip_email and should_send_email_notification(email_anonymous_id, config_file_path):
        if not hide_individual_names:
            console.print(
                "\n[bold yellow]⚠️  --email-anonymous-id requires --hide-individual-names[/bold yellow]"
            )
            console.print("[yellow]   Email notifications skipped.[/yellow]")
        else:
            console.print("\n[bold]Step 2.5/3:[/bold] Sending email notifications...")

            send_email_notifications_cli(
                config_file_path=config_file_path,
                report_context="PR Report Generated",
                console=console,
                mail_save_file=mail_save_file,
            )

    # Step 2.8: Generate Visualizations
    generate_visualization_for_report(
        config_file_path=config_file_path,
        no_visualization=no_visualization,
        no_upload=no_upload,
        report_type="pr",
        failed_steps=failed_steps,
    )

    # Step 3: Claude Insights (opt-in)
    if with_claude_insights:
        console.print("\n[bold]Step 3/3:[/bold] Generating Claude insights...")
        pr_reports = list(Path("reports/github").glob("combined_pr_report_*.tsv"))
        if pr_reports:
            latest_pr = max(pr_reports, key=lambda p: p.stat().st_mtime)

            # Build args for analyze script
            analyze_args = ["--report", str(latest_pr)]
            if no_upload:
                analyze_args.append("--no-upload")
            if claude_api_mode:
                analyze_args.append("--claude-api-mode")

            if (
                run_script(
                    "impactlens.scripts.analyze_with_claude_code",
                    analyze_args,
                    f"Claude insights: {latest_pr.name}",
                )
                != 0
            ):
                failed_steps.append("PR Claude insights")
    else:
        console.print(
            "\n[bold yellow]ℹ️  Claude insights skipped[/bold yellow] (use --with-claude-insights to enable)"
        )

    # Summary
    console.print("\n" + "=" * 60)
    if failed_steps:
        console.print(
            f"[bold yellow]⚠ Workflow completed with {len(failed_steps)} failures:[/bold yellow]"
        )
        for step in failed_steps:
            console.print(f"  [red]✗[/red] {step}")
        return 1
    else:
        console.print("[bold green]✓ PR full workflow completed successfully![/bold green]")
        return 0


@pr_app.command(name="full")
def pr_full(
    config: Optional[str] = typer.Option(
        None,
        "--config",
        help="Config file path or directory (e.g., config/team-a/pr_report_config.yaml or config/team-a)",
    ),
    incremental: bool = typer.Option(False, "--incremental", help="Only fetch new/updated PRs"),
    no_upload: bool = typer.Option(False, "--no-upload", help="Skip uploading to Google Sheets"),
    upload_members: bool = typer.Option(
        False,
        "--upload-members",
        help="Upload individual member reports (default: only team/combined)",
    ),
    hide_individual_names: bool = typer.Option(
        False,
        "--hide-individual-names",
        help="Anonymize individual names in combined reports and hide sensitive fields",
    ),
    email_anonymous_id: bool = typer.Option(
        False,
        "--email-anonymous-id",
        help="Email each member ONLY their own anonymous ID (requires --hide-individual-names)",
    ),
    mail_save_file: Optional[str] = typer.Option(
        None,
        "--mail-save-file",
        help="Save emails to files instead of sending them (specify directory path)",
    ),
    with_claude_insights: bool = typer.Option(
        False, "--with-claude-insights", help="Generate insights using Claude Code (requires setup)"
    ),
    claude_api_mode: bool = typer.Option(
        False,
        "--claude-api-mode",
        help="Use Anthropic API instead of Claude Code CLI (requires ANTHROPIC_API_KEY)",
    ),
    no_visualization: bool = typer.Option(
        False,
        "--no-visualization",
        help="Skip generating charts and HTML visualization report",
    ),
):
    """
    Complete PR workflow: generate all reports and combine.

    Workflow: Team → Members → Combine → Upload (Claude insights optional with --with-claude-insights)

    Config parameter:
    - Directory: config/team-a (auto-finds pr_report_config.yaml)
    - Specific file: config/team-a/pr_report_config.yaml
    """
    exit_code = _pr_full_impl(
        config=config,
        incremental=incremental,
        no_upload=no_upload,
        upload_members=upload_members,
        hide_individual_names=hide_individual_names,
        email_anonymous_id=email_anonymous_id,
        mail_save_file=mail_save_file,
        with_claude_insights=with_claude_insights,
        claude_api_mode=claude_api_mode,
        no_visualization=no_visualization,
    )
    sys.exit(exit_code)


# ============================================================================
# Global Commands
# ============================================================================


@app.command(name="full")
def full_workflow(
    config: Optional[str] = typer.Option(
        None,
        "--config",
        help="Config directory (e.g., config/team-a) or specific config file",
    ),
    no_upload: bool = typer.Option(False, "--no-upload", help="Skip uploading to Google Sheets"),
    upload_members: bool = typer.Option(
        False,
        "--upload-members",
        help="Upload individual member reports (default: only team/combined)",
    ),
    hide_individual_names: bool = typer.Option(
        False,
        "--hide-individual-names",
        help="Anonymize individual names in combined reports (Developer-1, Developer-2, etc.)",
    ),
    email_anonymous_id: bool = typer.Option(
        False,
        "--email-anonymous-id",
        help="Email each member ONLY their own anonymous ID (requires --hide-individual-names)",
    ),
    mail_save_file: Optional[str] = typer.Option(
        None,
        "--mail-save-file",
        help="Save emails to files instead of sending them (specify directory path)",
    ),
    with_claude_insights: bool = typer.Option(
        False, "--with-claude-insights", help="Generate insights using Claude Code (requires setup)"
    ),
    incremental: bool = typer.Option(False, "--incremental", help="Only fetch new/updated PRs"),
    claude_api_mode: bool = typer.Option(
        False,
        "--claude-api-mode",
        help="Use Anthropic API instead of Claude Code CLI (requires ANTHROPIC_API_KEY)",
    ),
    no_visualization: bool = typer.Option(
        False,
        "--no-visualization",
        help="Skip generating charts and HTML visualization report",
    ),
    log_level: str = typer.Option(
        "WARNING",
        "--log-level",
        help="Logging level: DEBUG, INFO, WARNING, ERROR (default: WARNING)",
    ),
):
    """
    Complete workflow: Execute both Jira full + PR full workflows.

    Workflow: Jira (Team → Members → Combine) + PR (Team → Members → Combine) → Upload
    (Claude insights optional with --with-claude-insights)

    Config parameter:
    - Directory: config/team-a (auto-finds both jira_report_config.yaml and pr_report_config.yaml)
    - Specific file: Uses for both workflows
    """
    # Set log level early
    set_log_level(log_level)

    console.print(
        Panel.fit(
            "[bold white]Complete AI Impact Analysis[/bold white]\n"
            "[dim]Jira Full → PR Full → All Reports Generated[/dim]",
            border_style="white",
        )
    )

    # Resolve config paths (directory or specific files)
    jira_config_path, pr_config_path = resolve_config_paths_for_full(config)

    failed_workflows = []

    # Jira Full Workflow
    console.print("\n" + "=" * 60)
    console.print("[bold cyan]JIRA WORKFLOW[/bold cyan]")
    console.print("=" * 60)

    jira_exit_code = _jira_full_impl(
        config=str(jira_config_path) if jira_config_path else None,
        no_upload=no_upload,
        upload_members=upload_members,
        hide_individual_names=hide_individual_names,
        email_anonymous_id=email_anonymous_id,
        mail_save_file=mail_save_file,
        with_claude_insights=with_claude_insights,
        claude_api_mode=claude_api_mode,
        no_visualization=no_visualization,
        skip_email=True,  # Skip email in individual workflows, send once at end
    )

    if jira_exit_code != 0:
        failed_workflows.append("Jira workflow")

    # PR Full Workflow
    console.print("\n" + "=" * 60)
    console.print("[bold magenta]PR WORKFLOW[/bold magenta]")
    console.print("=" * 60)

    pr_exit_code = _pr_full_impl(
        config=str(pr_config_path) if pr_config_path else None,
        incremental=incremental,
        no_upload=no_upload,
        upload_members=upload_members,
        hide_individual_names=hide_individual_names,
        email_anonymous_id=email_anonymous_id,
        mail_save_file=mail_save_file,
        with_claude_insights=with_claude_insights,
        claude_api_mode=claude_api_mode,
        no_visualization=no_visualization,
        skip_email=True,  # Skip email in individual workflows, send once at end
    )

    if pr_exit_code != 0:
        failed_workflows.append("PR workflow")

    # Check if aggregation config exists and run aggregation
    # Look for aggregation_config.yaml in two places:
    # 1. Same directory as the config files (for single team)
    # 2. Parent directory (for multi-team with aggregation at parent level)
    config_dir = None
    if jira_config_path:
        config_dir = jira_config_path.parent
    elif pr_config_path:
        config_dir = pr_config_path.parent

    aggregation_config = None
    if config_dir:
        # Try current directory first
        aggregation_config = config_dir / "aggregation_config.yaml"
        if not aggregation_config.exists():
            # Try parent directory
            aggregation_config = config_dir.parent / "aggregation_config.yaml"

        if aggregation_config.exists():
            console.print("\n" + "=" * 60)
            console.print("[bold cyan]AGGREGATION[/bold cyan]")
            console.print("=" * 60)
            console.print(f"[dim]Found aggregation config: {aggregation_config}[/dim]\n")

            try:
                aggregator = ReportAggregator(str(aggregation_config))

                # Aggregate Jira reports
                console.print("[cyan]Aggregating Jira reports...[/cyan]")
                jira_output = aggregator.aggregate_jira_reports()
                if jira_output:
                    console.print(
                        f"[green]✓ Jira aggregation completed: {jira_output.name}[/green]"
                    )
                    # Upload aggregated Jira report
                    upload_to_google_sheets(jira_output, skip_upload=no_upload)
                else:
                    console.print("[yellow]⚠ No Jira reports found for aggregation[/yellow]")

                # Aggregate PR reports
                console.print("[cyan]Aggregating PR reports...[/cyan]")
                pr_output = aggregator.aggregate_pr_reports()
                if pr_output:
                    console.print(f"[green]✓ PR aggregation completed: {pr_output.name}[/green]")
                    # Upload aggregated PR report
                    upload_to_google_sheets(pr_output, skip_upload=no_upload)
                else:
                    console.print("[yellow]⚠ No PR reports found for aggregation[/yellow]")

            except Exception as e:
                console.print(f"[red]Error during aggregation: {e}[/red]")
                failed_workflows.append("Aggregation")

    # Email Notifications (opt-in, only with anonymization, sent once at the end)
    config_to_use = jira_config_path or pr_config_path
    if should_send_email_notification(email_anonymous_id, config_to_use):
        if not hide_individual_names:
            console.print(
                "\n[bold yellow]⚠️  --email-anonymous-id requires --hide-individual-names[/bold yellow]"
            )
            console.print("[yellow]   Email notifications skipped.[/yellow]")
        else:
            console.print("\n" + "=" * 60)
            console.print("[bold]EMAIL NOTIFICATIONS[/bold]")
            console.print("=" * 60)

            send_email_notifications_cli(
                config_file_path=config_to_use,
                report_context="Full Report Generated (Jira + PR)",
                console=console,
                mail_save_file=mail_save_file,
            )

    # Final Summary
    console.print("\n" + "=" * 60)
    if failed_workflows:
        console.print(
            f"[bold yellow]⚠ Workflow completed with {len(failed_workflows)} failures:[/bold yellow]"
        )
        for workflow in failed_workflows:
            console.print(f"  [red]✗[/red] {workflow}")
        sys.exit(1)
    else:
        console.print("[bold green]✓ Complete workflow finished successfully![/bold green]")
        console.print("\n[dim]All reports generated in reports/ directory[/dim]")
        sys.exit(0)


@app.command()
def aggregate(
    config: str = typer.Option(..., "--config", help="Path to aggregation config file"),
    jira_only: bool = typer.Option(False, "--jira-only", help="Aggregate only Jira reports"),
    pr_only: bool = typer.Option(False, "--pr-only", help="Aggregate only PR reports"),
):
    """Aggregate multiple project reports into unified reports."""
    console.print(
        Panel.fit(
            "[bold green]Report Aggregation[/bold green]\n"
            "[dim]Merging multiple project reports into unified reports[/dim]",
            border_style="green",
        )
    )

    args = ["--config", config]
    if jira_only:
        args.append("--jira-only")
    if pr_only:
        args.append("--pr-only")

    return_code = run_script("impactlens.scripts.aggregate_reports", args, "Aggregating reports")
    sys.exit(return_code)


# Add alias 'agg' for aggregate
app.command(name="agg")(aggregate)


@app.command()
def verify():
    """Verify setup and configuration."""
    console.print(Panel.fit("[bold blue]Setup Verification[/bold blue]", border_style="blue"))

    script = "impactlens.scripts.verify_setup"
    return_code = run_script(script, [], "Verifying setup")
    sys.exit(return_code)


@app.command()
def clear_sheets(
    spreadsheet_id: Optional[str] = typer.Option(
        None,
        "--spreadsheet-id",
        help="Google Spreadsheet ID (or use GOOGLE_SPREADSHEET_ID env var)",
    ),
    clear_first: bool = typer.Option(
        False, "--clear-first-sheet", help="Also clear content from the first sheet"
    ),
    rename_first: Optional[str] = typer.Option(
        None, "--rename-first-sheet", help="Rename the first sheet (e.g., 'Main')"
    ),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
):
    """Clear all sheets from Google Spreadsheet (DESTRUCTIVE!)."""
    console.print(
        Panel.fit(
            "[bold red]Google Sheets Cleaner[/bold red]\n"
            "[dim]Delete all sheets except the first one[/dim]",
            border_style="red",
        )
    )

    args = []
    if spreadsheet_id:
        args.extend(["--spreadsheet-id", spreadsheet_id])
    if clear_first:
        args.append("--clear-first-sheet")
    if rename_first:
        args.extend(["--rename-first-sheet", rename_first])
    if yes:
        args.append("--yes")

    script = "impactlens.scripts.clear_google_sheets"
    return_code = run_script(script, args, "Clearing Google Sheets")
    sys.exit(return_code)


@app.command()
def version():
    """Show version information."""
    console.print(
        Panel.fit(
            "[bold]AI Impact Analysis[/bold]\n"
            "Version: 1.0.0\n\n"
            "Measure the impact of AI tools on development efficiency",
            border_style="blue",
        )
    )


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """
    AI Impact Analysis CLI - Measure AI tool impact on development efficiency.

    Use subcommands to generate reports, analyze data, and more.
    """
    if ctx.invoked_subcommand is None:
        # Show help if no command provided
        console.print(
            Panel.fit(
                "[bold]AI Impact Analysis Tool[/bold]\n\n"
                "Generate reports to measure the impact of AI coding assistants.\n\n"
                "Quick Start:\n"
                "  [cyan]impactlens jira full[/cyan]     - Complete Jira workflow\n"
                "  [magenta]impactlens pr full[/magenta]       - Complete PR workflow\n"
                "  [white]impactlens full[/white]          - Complete Jira + PR workflow\n\n"
                "Use --help with any command for more information.",
                border_style="blue",
            )
        )

        # Show available commands
        table = Table(title="Available Commands", show_header=True, header_style="bold")
        table.add_column("Command", style="cyan", width=20)
        table.add_column("Description", style="dim")

        table.add_row("jira", "Jira issue analysis (team, member, members, all, combine, full)")
        table.add_row("pr", "GitHub PR analysis (team, member, members, all, combine, full)")
        table.add_row("full", "Complete workflow: Jira + PR")
        table.add_row("aggregate (agg)", "Aggregate multiple project reports into unified reports")
        table.add_row("clear-sheets", "Clear all sheets from Google Spreadsheet (DESTRUCTIVE!)")
        table.add_row("verify", "Verify setup and configuration")
        table.add_row("version", "Show version information")

        console.print(table)
        console.print("\n[dim]Run 'impactlens <command> --help' for detailed usage[/dim]")


if __name__ == "__main__":
    app()
