#!/usr/bin/env python3
"""
AI Report Analyzer using Claude Code

Automatically analyzes reports by calling Claude Code CLI in non-interactive mode.
The analysis is generated, displayed, and saved to file automatically.

Usage:
    # Automatic mode (default): calls Claude Code CLI to generate analysis
    python -m ai_impact_analysis.scripts.analyze_with_claude_code \\
      --report reports/github/combined_pr_report_*.tsv

    # Manual mode: only displays the prompt for manual copy-paste
    python -m ai_impact_analysis.scripts.analyze_with_claude_code \\
      --report reports/github/combined_pr_report_*.tsv \\
      --manual

    # With custom timeout (default: 300 seconds)
    python -m ai_impact_analysis.scripts.analyze_with_claude_code \\
      --report reports/github/combined_pr_report_*.tsv \\
      --timeout 600
"""

import os
import sys
import argparse
import yaml
import subprocess
import json
from pathlib import Path
from datetime import datetime
from glob import glob

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ai_impact_analysis.utils.report_preprocessor import ReportPreprocessor
from ai_impact_analysis.utils.logger import logger


def find_latest_report(report_pattern: str) -> str:
    """Find the most recent report matching the pattern."""
    matches = glob(report_pattern)

    if not matches:
        raise FileNotFoundError(f"No reports found matching: {report_pattern}")

    # Sort by modification time (most recent first)
    matches.sort(key=os.path.getmtime, reverse=True)
    return matches[0]


def load_prompt_template(template_path: str = "config/analysis_prompt_template.yaml") -> dict:
    """Load the analysis prompt template from YAML config."""
    try:
        with open(template_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logger.warning(f"Prompt template not found at {template_path}, using default")
        return None


def read_report_content(report_path: str) -> str:
    """Read the full TSV report content."""
    with open(report_path, "r", encoding="utf-8") as f:
        return f.read()


def create_analysis_prompt(report_path: str, preprocessed_data: dict, template: dict = None) -> str:
    """Create a comprehensive analysis prompt using the template."""
    report_type = preprocessed_data["report_type"]
    summary = preprocessed_data["summary"]
    report_name = Path(report_path).name

    # Read the full report
    full_report = read_report_content(report_path)

    # Use template if provided, otherwise use default
    if template:
        sections = template.get("sections", {})
        output_format = template.get("output_format", {})
        custom_focus = template.get("custom_focus", "")
    else:
        sections = None
        output_format = None
        custom_focus = ""

    # Build prompt
    prompt_lines = []

    # Header
    if template:
        prompt_lines.append(template.get("introduction", "").strip())
    else:
        prompt_lines.append(
            "I need you to analyze this engineering metrics report and provide actionable insights."
        )

    prompt_lines.append("")
    prompt_lines.append("## REPORT INFORMATION")
    prompt_lines.append(f"- **File**: {report_name}")
    prompt_lines.append(f"- **Type**: {report_type.upper()} Metrics Report")
    prompt_lines.append(f"- **Phases**: {', '.join(preprocessed_data['phases'])}")
    prompt_lines.append(f"- **Metrics**: {len(preprocessed_data['metrics'])} tracked")
    prompt_lines.append("")

    prompt_lines.append("## FULL REPORT DATA")
    prompt_lines.append("")
    prompt_lines.append("```")
    prompt_lines.append(full_report)
    prompt_lines.append("```")
    prompt_lines.append("")

    prompt_lines.append("## PREPROCESSED SUMMARY")
    prompt_lines.append("")
    prompt_lines.append(summary)
    prompt_lines.append("")

    prompt_lines.append("## ANALYSIS REQUIREMENTS")
    prompt_lines.append("")
    prompt_lines.append("Please provide a comprehensive analysis with the following sections:")
    prompt_lines.append("")

    # Add sections from template or default
    if sections:
        # Section 1: Key Trends
        kt = sections.get("key_trends", {})
        prompt_lines.append(
            f"### 1. {kt.get('title', 'KEY TRENDS')} ({kt.get('count', '3-5 insights')})"
        )
        prompt_lines.append(kt.get("description", ""))
        for q in kt.get("questions", []):
            prompt_lines.append(f"- {q}")
        prompt_lines.append("")

        # Section 2: Bottlenecks & Risks
        br = sections.get("bottlenecks_risks", {})
        prompt_lines.append(
            f"### 2. {br.get('title', 'BOTTLENECKS & RISKS')} ({br.get('count', '2-3 items')})"
        )
        prompt_lines.append(br.get("description", ""))
        for q in br.get("questions", []):
            prompt_lines.append(f"- {q}")
        prompt_lines.append("")

        # Section 3: Recommendations
        rec = sections.get("recommendations", {})
        prompt_lines.append(
            f"### 3. {rec.get('title', 'ACTIONABLE RECOMMENDATIONS')} ({rec.get('count', '2-3 items')})"
        )
        prompt_lines.append(rec.get("description", ""))
        for req in rec.get("requirements", []):
            prompt_lines.append(f"- {req}")
        prompt_lines.append("")

        # Section 4: Impact Assessment (report-type specific)
        ia = sections.get("impact_assessment", {})
        if report_type == "github":
            gh = ia.get("github", {})
            prompt_lines.append(f"### 4. {gh.get('title', 'AI TOOL IMPACT ASSESSMENT')}")
            for q in gh.get("questions", []):
                prompt_lines.append(f"- {q}")
        else:
            jira = ia.get("jira", {})
            prompt_lines.append(f"### 4. {jira.get('title', 'WORKFLOW EFFICIENCY ANALYSIS')}")
            for q in jira.get("questions", []):
                prompt_lines.append(f"- {q}")
        prompt_lines.append("")
    else:
        # Default sections (fallback)
        prompt_lines.append("### 1. KEY TRENDS (3-5 key insights)")
        prompt_lines.append("### 2. BOTTLENECKS & RISKS (2-3 critical items)")
        prompt_lines.append("### 3. ACTIONABLE RECOMMENDATIONS (2-3 concrete action items)")
        if report_type == "github":
            prompt_lines.append("### 4. AI TOOL IMPACT ASSESSMENT")
        else:
            prompt_lines.append("### 4. WORKFLOW EFFICIENCY ANALYSIS")
        prompt_lines.append("")

    # Output format
    prompt_lines.append("## OUTPUT FORMAT")
    prompt_lines.append("")
    if output_format:
        prompt_lines.append(
            f"Please structure your analysis with {output_format.get('structure', 'numbered sections')}."
        )
        prompt_lines.append("Focus on:")
        for focus in output_format.get("focus_areas", []):
            prompt_lines.append(f"- {focus}")
        prompt_lines.append("")
        prompt_lines.append(f"Tone: {output_format.get('tone', 'Professional and accessible')}")
    else:
        prompt_lines.append("Please structure your analysis clearly with numbered sections.")
        prompt_lines.append("Focus on business impact and concrete actions.")

    prompt_lines.append("")

    # Custom focus
    if custom_focus:
        prompt_lines.append("## ADDITIONAL FOCUS")
        prompt_lines.append("")
        prompt_lines.append(custom_focus)
        prompt_lines.append("")

    return "\n".join(prompt_lines)


def call_claude_code(prompt: str, timeout: int = 300) -> str:
    """
    Call Claude Code CLI in non-interactive mode to analyze the prompt.

    Args:
        prompt: The analysis prompt to send to Claude
        timeout: Timeout in seconds (default: 300 = 5 minutes)

    Returns:
        Analysis text from Claude Code

    Raises:
        RuntimeError: If claude command fails
        FileNotFoundError: If claude command not found
    """
    logger.info("🤖 Calling Claude Code for analysis...")
    logger.info(f"   Timeout: {timeout}s")

    try:
        # Call claude with -p (print mode) for non-interactive execution
        # Pass prompt via stdin (more reliable for long prompts)
        result = subprocess.run(
            [
                "claude",
                "-p",  # Non-interactive print mode
                "--output-format",
                "text",  # Plain text output
                "--tools",
                "Read",  # Allow Read tool only (safer)
            ],
            input=prompt,  # Pass prompt via stdin
            capture_output=True,
            text=True,
            timeout=timeout,
            check=True,
        )

        analysis = result.stdout.strip()

        if not analysis:
            raise RuntimeError("Claude Code returned empty response")

        logger.info("   ✓ Analysis completed successfully")
        return analysis

    except FileNotFoundError:
        raise FileNotFoundError(
            "Claude Code CLI not found. Please install it first:\n"
            "  curl -fsSL https://claude.ai/install.sh | bash\n"
            "  OR: npm install -g @anthropic-ai/claude-code"
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"Claude Code analysis timed out after {timeout}s")
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr if e.stderr else "Unknown error"
        raise RuntimeError(f"Claude Code failed: {error_msg}")


def save_analysis(analysis_text: str, report_path: str, output_dir: str = "reports") -> str:
    """Save analysis to file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Determine report type for filename
    if "github" in report_path.lower():
        prefix = "ai_analysis_pr"
        report_type = "GITHUB PR"
    else:
        prefix = "ai_analysis_jira"
        report_type = "JIRA"

    output_filename = f"{prefix}_{timestamp}.txt"
    output_path = Path(output_dir) / output_filename
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Format the final report
    report_lines = []
    report_lines.append("=" * 80)
    report_lines.append("AI-POWERED METRICS ANALYSIS REPORT")
    report_lines.append("=" * 80)
    report_lines.append("")
    report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append(f"Report Type: {report_type}")
    report_lines.append(f"Analysis Tool: Claude Code")
    report_lines.append(f"Source Report: {Path(report_path).name}")
    report_lines.append("")
    report_lines.append("=" * 80)
    report_lines.append("")
    report_lines.append(analysis_text)
    report_lines.append("")
    report_lines.append("=" * 80)
    report_lines.append(f"Report saved: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("=" * 80)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))

    return str(output_path)


def main():
    parser = argparse.ArgumentParser(
        description="Analyze reports using Claude Code CLI (automatic or manual mode)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Automatic mode: calls Claude Code to generate analysis
  python -m ai_impact_analysis.scripts.analyze_with_claude_code \\
    --report "reports/github/combined_pr_report_*.tsv"

  # Manual mode: only shows prompt for copy-paste
  python -m ai_impact_analysis.scripts.analyze_with_claude_code \\
    --report "reports/github/combined_pr_report_*.tsv" \\
    --manual

  # With custom prompt template and timeout
  python -m ai_impact_analysis.scripts.analyze_with_claude_code \\
    --report "reports/jira/combined_jira_report_*.tsv" \\
    --prompt-template config/my_custom_prompt.yaml \\
    --timeout 600

  # Save pre-generated analysis directly
  python -m ai_impact_analysis.scripts.analyze_with_claude_code \\
    --report "reports/github/combined_pr_report_*.tsv" \\
    --save-analysis "Your analysis text here"
        """,
    )

    parser.add_argument(
        "--report",
        type=str,
        required=True,
        help="Path to TSV report (supports wildcards for latest)",
    )

    parser.add_argument(
        "--prompt-template",
        type=str,
        default="config/analysis_prompt_template.yaml",
        help="Path to prompt template YAML file",
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        default="reports",
        help="Output directory for analysis",
    )

    parser.add_argument(
        "--save-analysis",
        type=str,
        help="Analysis text to save directly (optional, skips Claude Code call)",
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Timeout for Claude Code analysis in seconds (default: 300)",
    )

    parser.add_argument(
        "--manual",
        action="store_true",
        help="Manual mode: only generate and display prompt without calling Claude Code",
    )

    args = parser.parse_args()

    logger.info("=" * 80)
    logger.info("AI Report Analyzer (Claude Code Edition)")
    logger.info("=" * 80)
    logger.info("")

    # Find report file
    report_path = find_latest_report(args.report)
    logger.info(f"📊 Report: {Path(report_path).name}")
    logger.info("")

    # Load prompt template
    logger.info("📝 Loading prompt template...")
    template = load_prompt_template(args.prompt_template)
    if template:
        logger.info(f"   ✓ Loaded: {args.prompt_template}")
    else:
        logger.info("   ⚠ Using default prompt structure")
    logger.info("")

    # Preprocess report
    logger.info("🔄 Preprocessing report...")
    preprocessor = ReportPreprocessor(report_path)
    preprocessed_data = preprocessor.load_and_parse()

    logger.info(f"   Type: {preprocessed_data['report_type'].upper()}")
    logger.info(f"   Phases: {', '.join(preprocessed_data['phases'])}")
    logger.info(f"   Metrics: {len(preprocessed_data['metrics'])} tracked")
    logger.info("")

    # Generate analysis prompt
    logger.info("✨ Generating analysis prompt...")
    prompt = create_analysis_prompt(report_path, preprocessed_data, template)

    # If analysis text provided, save it directly
    if args.save_analysis:
        logger.info("")
        logger.info("💾 Saving provided analysis...")
        output_file = save_analysis(args.save_analysis, report_path, args.output_dir)
        logger.info(f"   ✓ Saved to: {output_file}")
        logger.info("")
        logger.info("📤 To upload to Google Sheets:")
        logger.info(
            f"   python -m ai_impact_analysis.scripts.upload_to_sheets --report {output_file}"
        )
        logger.info("")
        return 0

    # Manual mode: just display the prompt
    if args.manual:
        logger.info("")
        logger.info("=" * 80)
        logger.info("🎯 MANUAL MODE: ANALYSIS PROMPT")
        logger.info("=" * 80)
        logger.info("")
        print(prompt)
        logger.info("")
        logger.info("=" * 80)
        logger.info("📋 NEXT STEPS")
        logger.info("=" * 80)
        logger.info("")
        logger.info("1. Copy the analysis prompt above")
        logger.info("2. Run: claude")
        logger.info("3. Paste the prompt to get analysis")
        logger.info("4. Save the result using --save-analysis flag")
        logger.info("")
        return 0

    # Automatic mode: call Claude Code
    logger.info("")
    logger.info("=" * 80)
    logger.info("🚀 AUTOMATIC ANALYSIS MODE")
    logger.info("=" * 80)
    logger.info("")

    try:
        # Call Claude Code to analyze
        analysis = call_claude_code(prompt, timeout=args.timeout)

        logger.info("")
        logger.info("=" * 80)
        logger.info("📊 ANALYSIS RESULT")
        logger.info("=" * 80)
        logger.info("")
        print(analysis)
        logger.info("")

        # Save analysis automatically
        logger.info("💾 Saving analysis to file...")
        output_file = save_analysis(analysis, report_path, args.output_dir)
        logger.info(f"   ✓ Saved to: {output_file}")
        logger.info("")

        # Show upload command
        logger.info("=" * 80)
        logger.info("✅ ANALYSIS COMPLETE!")
        logger.info("=" * 80)
        logger.info("")
        logger.info(f"📄 Report: {Path(report_path).name}")
        logger.info(f"💾 Output: {output_file}")
        logger.info("")
        logger.info("📤 To upload to Google Sheets:")
        logger.info(
            f"   python -m ai_impact_analysis.scripts.upload_to_sheets --report {output_file}"
        )
        logger.info("")
        logger.info("=" * 80)

        return 0

    except Exception as e:
        logger.error("")
        logger.error("=" * 80)
        logger.error("❌ ANALYSIS FAILED")
        logger.error("=" * 80)
        logger.error("")
        logger.error(f"Error: {str(e)}")
        logger.error("")
        logger.error("💡 TIP: Try manual mode instead:")
        logger.error(f"   python -m ai_impact_analysis.scripts.analyze_with_claude_code \\")
        logger.error(f'     --report "{report_path}" \\')
        logger.error(f"     --manual")
        logger.error("")
        return 1


if __name__ == "__main__":
    sys.exit(main())
