#!/usr/bin/env python3
"""
AI Impact Analysis - Unified CLI Interface.

This module provides a unified command-line interface for all AI impact analysis operations.
It uses clear subcommands to avoid ambiguity and ensure consistent behavior.
"""

import sys
import subprocess
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Main app
app = typer.Typer(
    name="ai-impact-analysis",
    help="AI Impact Analysis Tool - Measure the impact of AI tools on development efficiency",
    add_completion=False,
)

# Subcommands for Jira and PR
jira_app = typer.Typer(help="Jira issue analysis commands")
pr_app = typer.Typer(help="GitHub PR analysis commands")

app.add_typer(jira_app, name="jira")
app.add_typer(pr_app, name="pr")

console = Console()


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

    script = "ai_impact_analysis.scripts.generate_jira_report"
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

    script = "ai_impact_analysis.scripts.generate_jira_report"
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

    script = "ai_impact_analysis.scripts.generate_jira_report"
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

    script = "ai_impact_analysis.scripts.generate_jira_report"
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

    script = "ai_impact_analysis.scripts.generate_jira_report"
    return_code = run_script(script, args, "Combining Jira reports")
    sys.exit(return_code)


@jira_app.command(name="full")
def jira_full(
    config: Optional[str] = typer.Option(None, "--config", help="Custom config file path"),
    no_upload: bool = typer.Option(False, "--no-upload", help="Skip uploading to Google Sheets"),
    with_claude_insights: bool = typer.Option(
        False, "--with-claude-insights", help="Generate insights using Claude Code (requires setup)"
    ),
    claude_api_mode: bool = typer.Option(
        False,
        "--claude-api-mode",
        help="Use Anthropic API instead of Claude Code CLI (requires ANTHROPIC_API_KEY)",
    ),
):
    """
    Complete Jira workflow: generate all reports and combine.

    This command executes: team reports → member reports → combine → upload all.

    Claude insights are DISABLED by default. Use --with-claude-insights to enable.

    Generates N+2 files: N member reports + 1 team + 1 combined.
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

    failed_steps = []

    # Step 1: Generate team + all members
    console.print("\n[bold]Step 1/3:[/bold] Generating team + members reports...")
    args = ["--all-members"]
    if config:
        args.extend(["--config", config])
    if no_upload:
        args.append("--no-upload")

    if run_script("ai_impact_analysis.scripts.generate_jira_report", args, "Jira all reports") != 0:
        failed_steps.append("Jira all reports")

    # Step 2: Combine reports
    console.print("\n[bold]Step 2/3:[/bold] Combining reports...")
    args = ["--combine-only"]
    if config:
        args.extend(["--config", config])
    if no_upload:
        args.append("--no-upload")

    if run_script("ai_impact_analysis.scripts.generate_jira_report", args, "Jira combine") != 0:
        failed_steps.append("Jira combine")

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
                    "ai_impact_analysis.scripts.analyze_with_claude_code",
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
        sys.exit(1)
    else:
        console.print("[bold green]✓ Jira full workflow completed successfully![/bold green]")
        sys.exit(0)


# ============================================================================
# PR Commands
# ============================================================================


@pr_app.command(name="team")
def pr_team(
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
    if incremental:
        args.append("--incremental")
    if no_upload:
        args.append("--no-upload")

    script = "ai_impact_analysis.scripts.generate_pr_report"
    return_code = run_script(script, args, "Generating PR team report")
    sys.exit(return_code)


@pr_app.command(name="member")
def pr_member(
    username: str = typer.Argument(..., help="GitHub username (e.g., wlin)"),
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
    if incremental:
        args.append("--incremental")
    if no_upload:
        args.append("--no-upload")

    script = "ai_impact_analysis.scripts.generate_pr_report"
    return_code = run_script(script, args, f"Generating PR report for {username}")
    sys.exit(return_code)


@pr_app.command(name="members")
def pr_members(
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
    if incremental:
        args.append("--incremental")
    if no_upload:
        args.append("--no-upload")

    script = "ai_impact_analysis.scripts.generate_pr_report"
    return_code = run_script(script, args, "Generating PR reports for all members")

    console.print(
        "\n[yellow]Note:[/yellow] This currently includes team report. "
        "Use 'pr all' for explicit team + members generation."
    )
    sys.exit(return_code)


@pr_app.command(name="all")
def pr_all(
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
    if incremental:
        args.append("--incremental")
    if no_upload:
        args.append("--no-upload")

    script = "ai_impact_analysis.scripts.generate_pr_report"
    return_code = run_script(script, args, "Generating PR team + members reports")
    sys.exit(return_code)


@pr_app.command(name="combine")
def pr_combine(
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
    if no_upload:
        args.append("--no-upload")

    script = "ai_impact_analysis.scripts.generate_pr_report"
    return_code = run_script(script, args, "Combining PR reports")
    sys.exit(return_code)


@pr_app.command(name="full")
def pr_full(
    incremental: bool = typer.Option(False, "--incremental", help="Only fetch new/updated PRs"),
    no_upload: bool = typer.Option(False, "--no-upload", help="Skip uploading to Google Sheets"),
    with_claude_insights: bool = typer.Option(
        False, "--with-claude-insights", help="Generate insights using Claude Code (requires setup)"
    ),
    claude_api_mode: bool = typer.Option(
        False,
        "--claude-api-mode",
        help="Use Anthropic API instead of Claude Code CLI (requires ANTHROPIC_API_KEY)",
    ),
):
    """
    Complete PR workflow: generate all reports and combine.

    This command executes: team reports → member reports → combine → upload all.

    Claude insights are DISABLED by default. Use --with-claude-insights to enable.

    Generates N+2 files: N member reports + 1 team + 1 combined.
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

    failed_steps = []

    # Step 1: Generate team + all members
    console.print("\n[bold]Step 1/3:[/bold] Generating team + members reports...")
    args = ["--all-members"]
    if incremental:
        args.append("--incremental")
    if no_upload:
        args.append("--no-upload")

    if run_script("ai_impact_analysis.scripts.generate_pr_report", args, "PR all reports") != 0:
        failed_steps.append("PR all reports")

    # Step 2: Combine reports
    console.print("\n[bold]Step 2/3:[/bold] Combining reports...")
    args = ["--combine-only"]
    if no_upload:
        args.append("--no-upload")

    if run_script("ai_impact_analysis.scripts.generate_pr_report", args, "PR combine") != 0:
        failed_steps.append("PR combine")

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
                    "ai_impact_analysis.scripts.analyze_with_claude_code",
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
        sys.exit(1)
    else:
        console.print("[bold green]✓ PR full workflow completed successfully![/bold green]")
        sys.exit(0)


# ============================================================================
# Global Commands
# ============================================================================


@app.command(name="full")
def full_workflow(
    no_upload: bool = typer.Option(False, "--no-upload", help="Skip uploading to Google Sheets"),
    with_claude_insights: bool = typer.Option(
        False, "--with-claude-insights", help="Generate insights using Claude Code (requires setup)"
    ),
    incremental: bool = typer.Option(False, "--incremental", help="Only fetch new/updated PRs"),
    claude_api_mode: bool = typer.Option(
        False,
        "--claude-api-mode",
        help="Use Anthropic API instead of Claude Code CLI (requires ANTHROPIC_API_KEY)",
    ),
):
    """
    Most comprehensive: Execute both Jira full + PR full workflows.

    This runs complete Jira analysis followed by complete PR analysis.

    Claude insights are DISABLED by default. Use --with-claude-insights to enable.

    Generates all Jira and GitHub PR reports.
    """
    console.print(
        Panel.fit(
            "[bold white]Complete AI Impact Analysis[/bold white]\n"
            "[dim]Jira Full → PR Full → All Reports Generated[/dim]",
            border_style="white",
        )
    )

    failed_workflows = []

    # Jira Full Workflow
    console.print("\n" + "=" * 60)
    console.print("[bold cyan]JIRA WORKFLOW[/bold cyan]")
    console.print("=" * 60)

    jira_args = ["--all-members"]
    if no_upload:
        jira_args.append("--no-upload")

    # Jira: all
    if run_script("ai_impact_analysis.scripts.generate_jira_report", jira_args, "Jira all") != 0:
        failed_workflows.append("Jira all")

    # Jira: combine
    jira_combine_args = ["--combine-only"]
    if no_upload:
        jira_combine_args.append("--no-upload")

    if (
        run_script(
            "ai_impact_analysis.scripts.generate_jira_report", jira_combine_args, "Jira combine"
        )
        != 0
    ):
        failed_workflows.append("Jira combine")

    # Jira: Claude insights (opt-in)
    if with_claude_insights:
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
                    "ai_impact_analysis.scripts.analyze_with_claude_code",
                    analyze_args,
                    f"Jira Claude insights",
                )
                != 0
            ):
                failed_workflows.append("Jira Claude insights")
    else:
        console.print(
            "\n[bold yellow]ℹ️  Jira Claude insights skipped[/bold yellow] (use --with-claude-insights to enable)"
        )

    # PR Full Workflow
    console.print("\n" + "=" * 60)
    console.print("[bold magenta]PR WORKFLOW[/bold magenta]")
    console.print("=" * 60)

    pr_args = ["--all-members"]
    if incremental:
        pr_args.append("--incremental")
    if no_upload:
        pr_args.append("--no-upload")

    # PR: all
    if run_script("ai_impact_analysis.scripts.generate_pr_report", pr_args, "PR all") != 0:
        failed_workflows.append("PR all")

    # PR: combine
    pr_combine_args = ["--combine-only"]
    if no_upload:
        pr_combine_args.append("--no-upload")

    if (
        run_script("ai_impact_analysis.scripts.generate_pr_report", pr_combine_args, "PR combine")
        != 0
    ):
        failed_workflows.append("PR combine")

    # PR: Claude insights (opt-in)
    if with_claude_insights:
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
                    "ai_impact_analysis.scripts.analyze_with_claude_code",
                    analyze_args,
                    f"PR Claude insights",
                )
                != 0
            ):
                failed_workflows.append("PR Claude insights")
    else:
        console.print(
            "\n[bold yellow]ℹ️  PR Claude insights skipped[/bold yellow] (use --with-claude-insights to enable)"
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
def verify():
    """Verify setup and configuration."""
    console.print(Panel.fit("[bold blue]Setup Verification[/bold blue]", border_style="blue"))

    script = "ai_impact_analysis.scripts.verify_setup"
    return_code = run_script(script, [], "Verifying setup")
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
                "  [cyan]ai-impact-analysis jira full[/cyan]     - Complete Jira workflow\n"
                "  [magenta]ai-impact-analysis pr full[/magenta]       - Complete PR workflow\n"
                "  [white]ai-impact-analysis full[/white]          - Complete Jira + PR workflow\n\n"
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
        table.add_row("verify", "Verify setup and configuration")
        table.add_row("version", "Show version information")

        console.print(table)
        console.print("\n[dim]Run 'ai-impact-analysis <command> --help' for detailed usage[/dim]")


if __name__ == "__main__":
    app()
