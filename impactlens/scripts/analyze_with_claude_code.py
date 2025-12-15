#!/usr/bin/env python3
"""
AI Report Analyzer using Claude (API or CLI)

Automatically analyzes reports using either:
1. Anthropic API (requires ANTHROPIC_API_KEY)
2. Claude Code CLI (requires claude command installed)

Usage:
    # Option 1: Use Claude Code CLI (default)
    python -m impactlens.scripts.analyze_with_claude_code \\
      --report reports/github/combined_pr_report_*.tsv

    # Option 2: Use Anthropic API with environment variable
    export ANTHROPIC_API_KEY="sk-ant-..."
    python -m impactlens.scripts.analyze_with_claude_code \\
      --report reports/github/combined_pr_report_*.tsv \\
      --claude-api-mode

    # Option 3: Use Anthropic API with explicit key parameter
    python -m impactlens.scripts.analyze_with_claude_code \\
      --report reports/github/combined_pr_report_*.tsv \\
      --claude-api-mode --anthropic-api-key "sk-ant-..."

    # Prompt preview mode: only displays the prompt without calling Claude
    python -m impactlens.scripts.analyze_with_claude_code \\
      --report reports/github/combined_pr_report_*.tsv \\
      --prompt-only
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

from impactlens.utils.report_preprocessor import ReportPreprocessor
from impactlens.utils.logger import logger
from impactlens.utils.workflow_utils import upload_to_google_sheets


def find_latest_report(report_pattern: str) -> str:
    """Find the most recent report matching the pattern."""
    matches = glob(report_pattern)

    if not matches:
        # Provide helpful error message with suggestions
        logger.error(f"❌ No reports found matching: {report_pattern}")
        logger.error("")
        logger.error("💡 Troubleshooting:")
        logger.error("   1. Check if the report file exists in the specified directory")
        logger.error("   2. Verify the file path is correct (use absolute or relative path)")
        logger.error("   3. If using wildcards (*), ensure at least one matching file exists")
        logger.error("")
        logger.error("📋 Common report locations:")
        logger.error("   - reports/combined_jira_report_*.tsv")
        logger.error("   - reports/combined_pr_report_*.tsv")
        logger.error("   - /path/to/downloaded/reports/combined_jira_report_*.tsv")
        logger.error("")
        logger.error("💡 To generate reports first, run:")
        logger.error("   impactlens jira full")
        logger.error("   impactlens pr full")
        logger.error("")
        sys.exit(1)

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


def call_anthropic_api(prompt: str, api_key: str = None, timeout: int = 300) -> str:
    """
    Call Anthropic API directly to analyze the prompt.

    Args:
        prompt: The analysis prompt to send to Claude
        api_key: Anthropic API key (if None, reads from ANTHROPIC_API_KEY env var)
        timeout: Timeout in seconds (default: 300 = 5 minutes)

    Returns:
        Analysis text from Claude API

    Raises:
        RuntimeError: If API call fails
        ValueError: If API key not provided
    """
    logger.info("🤖 Calling Anthropic API for analysis...")
    logger.info(f"   Timeout: {timeout}s")

    try:
        import anthropic
    except ImportError:
        raise ImportError(
            "anthropic library not installed. Install with:\n" "  pip install anthropic>=0.40.0"
        )

    # Get API key
    if not api_key:
        api_key = os.environ.get("ANTHROPIC_API_KEY")

    if not api_key:
        raise ValueError(
            "Anthropic API key not found. Either:\n"
            "  1. Set ANTHROPIC_API_KEY environment variable, or\n"
            "  2. Pass --anthropic-api-key parameter"
        )

    try:
        client = anthropic.Anthropic(api_key=api_key, timeout=timeout)

        response = client.messages.create(
            model="claude-sonnet-4-20250514",  # Latest Claude model
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )

        analysis = response.content[0].text.strip()

        if not analysis:
            raise RuntimeError("Anthropic API returned empty response")

        logger.info("   ✓ Analysis completed successfully")
        logger.info(f"   Model: {response.model}")
        logger.info(
            f"   Tokens: {response.usage.input_tokens} in, {response.usage.output_tokens} out"
        )

        return analysis

    except anthropic.APIError as e:
        raise RuntimeError(f"Anthropic API error: {e}")
    except Exception as e:
        raise RuntimeError(f"Anthropic API call failed: {e}")


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


def save_analysis(
    analysis_text: str,
    report_path: str,
    output_dir: str = "reports",
    analysis_tool: str = "Claude Code",
) -> str:
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
    report_lines.append(f"Analysis Tool: {analysis_tool}")
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
        description="Analyze reports using Claude (Anthropic API or Claude Code CLI)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use Claude Code CLI (default)
  python -m impactlens.scripts.analyze_with_claude_code \\
    --report "reports/github/combined_pr_report_*.tsv"

  # Use Anthropic API with environment variable
  export ANTHROPIC_API_KEY="sk-ant-..."
  python -m impactlens.scripts.analyze_with_claude_code \\
    --report "reports/github/combined_pr_report_*.tsv" \\
    --claude-api-mode

  # Use Anthropic API with explicit key parameter
  python -m impactlens.scripts.analyze_with_claude_code \\
    --report "reports/github/combined_pr_report_*.tsv" \\
    --claude-api-mode --anthropic-api-key "sk-ant-..."

  # Prompt preview mode: only shows prompt without calling Claude
  python -m impactlens.scripts.analyze_with_claude_code \\
    --report "reports/github/combined_pr_report_*.tsv" \\
    --prompt-only
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
        "--prompt-only",
        action="store_true",
        help="Prompt preview mode: only generate and display prompt without calling Claude",
    )

    parser.add_argument(
        "--no-upload",
        action="store_true",
        help="Skip uploading analysis to Google Sheets (default: auto-upload)",
    )

    parser.add_argument(
        "--claude-api-mode",
        action="store_true",
        help="Use Anthropic API instead of Claude Code CLI (requires ANTHROPIC_API_KEY)",
    )

    parser.add_argument(
        "--anthropic-api-key",
        type=str,
        help="Anthropic API key (if not provided, reads from ANTHROPIC_API_KEY env var)",
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
        # Auto-upload to Google Sheets (unless --no-upload specified)
        upload_to_google_sheets(Path(output_file), skip_upload=args.no_upload)

        return 0

    # Prompt preview mode: display and save the prompt
    if args.prompt_only:
        logger.info("")
        logger.info("=" * 80)
        logger.info("🎯 PROMPT PREVIEW MODE: ANALYSIS PROMPT")
        logger.info("=" * 80)
        logger.info("")
        print(prompt)
        logger.info("")

        # Save prompt to file
        report_name = Path(report_path).name
        output_dir_path = Path(args.output_dir)
        output_dir_path.mkdir(parents=True, exist_ok=True)
        prompt_file = output_dir_path / f"analysis_prompt_{report_name.replace('.tsv', '.txt')}"

        with open(prompt_file, "w", encoding="utf-8") as f:
            f.write(prompt)

        logger.info(f"💾 Prompt saved to: {prompt_file}")
        logger.info("")
        logger.info("=" * 80)
        logger.info("📋 NEXT STEPS")
        logger.info("=" * 80)
        logger.info("")
        logger.info("1. Copy the prompt from the file above")
        logger.info("2. Paste into any AI assistant (Claude, ChatGPT, Gemini, etc.)")
        logger.info("3. Get instant analysis and insights")
        logger.info("")
        return 0

    # Automatic mode: call Claude API or Claude Code
    logger.info("")
    logger.info("=" * 80)
    if args.claude_api_mode:
        logger.info("🚀 AUTOMATIC ANALYSIS MODE (Anthropic API)")
    else:
        logger.info("🚀 AUTOMATIC ANALYSIS MODE (Claude Code CLI)")
    logger.info("=" * 80)
    logger.info("")

    try:
        # Call Claude API or Claude Code based on mode
        if args.claude_api_mode:
            analysis = call_anthropic_api(
                prompt, api_key=args.anthropic_api_key, timeout=args.timeout
            )
        else:
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
        analysis_tool = (
            "Anthropic API (Claude Sonnet)" if args.claude_api_mode else "Claude Code CLI"
        )
        output_file = save_analysis(analysis, report_path, args.output_dir, analysis_tool)
        logger.info(f"   ✓ Saved to: {output_file}")
        logger.info("")

        # Auto-upload to Google Sheets (unless --no-upload specified)
        upload_to_google_sheets(Path(output_file), skip_upload=args.no_upload)

        # Summary
        logger.info("=" * 80)
        logger.info("✅ ANALYSIS COMPLETE!")
        logger.info("=" * 80)
        logger.info("")
        logger.info(f"📄 Report: {Path(report_path).name}")
        logger.info(f"💾 Output: {output_file}")
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
        logger.error("💡 TIP: Try prompt preview mode instead:")
        logger.error(f"   python -m impactlens.scripts.analyze_with_claude_code \\")
        logger.error(f'     --report "{report_path}" \\')
        logger.error(f"     --prompt-only")
        logger.error("")
        return 1


if __name__ == "__main__":
    sys.exit(main())
