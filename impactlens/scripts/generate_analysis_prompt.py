#!/usr/bin/env python3
"""
AI Report Analysis Prompt Generator

Generates analysis prompts from ImpactLens reports with intelligent detection:
- Single file input → Single report analysis prompt
- Directory input → Auto-detect combined (JIRA + PR) or single analysis

Usage:
    # Combined analysis (directory with JIRA + PR reports)
    python -m impactlens.scripts.generate_analysis_prompt \\
      --reports-dir "reports/team-name" \\
      --prompt-only

    # Single file analysis
    python -m impactlens.scripts.generate_analysis_prompt \\
      --reports-dir "reports/jira/combined_jira_report_*.tsv" \\
      --prompt-only
"""

import os
import sys
import argparse
import yaml
from pathlib import Path
from datetime import datetime
from glob import glob

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from impactlens.utils.report_preprocessor import ReportPreprocessor
from impactlens.utils.logger import logger


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


def find_reports_in_directory(directory: str) -> dict:
    """
    Find JIRA and PR reports in a directory for combined analysis.

    Priority:
    1. Aggregated reports (multi-team scenarios)
    2. Combined reports (single-team scenarios)

    Args:
        directory: Path to directory (e.g., reports/team-name/)

    Returns:
        dict with:
        - 'mode': 'combined' (both found), 'single' (one found), or 'none'
        - 'jira': path to JIRA report (if found)
        - 'pr': path to PR report (if found)
        - 'is_aggregated': True if aggregated reports, False otherwise
    """
    from glob import glob

    dir_path = Path(directory)

    # Priority 1: Search for aggregated reports (multi-team)
    jira_aggregated = list(glob(str(dir_path / "**/aggregated_jira_report_*.tsv"), recursive=True))
    pr_aggregated = list(glob(str(dir_path / "**/aggregated_pr_report_*.tsv"), recursive=True))

    # Priority 2: Search for combined reports (single-team)
    jira_combined = list(glob(str(dir_path / "**/combined_jira_report_*.tsv"), recursive=True))
    pr_combined = list(glob(str(dir_path / "**/combined_pr_report_*.tsv"), recursive=True))

    # Use aggregated if available, otherwise use combined
    if jira_aggregated or pr_aggregated:
        jira_reports = jira_aggregated
        pr_reports = pr_aggregated
        is_aggregated = True
    else:
        jira_reports = jira_combined
        pr_reports = pr_combined
        is_aggregated = False

    # Use most recent files if multiple found
    if jira_reports:
        jira_reports.sort(key=os.path.getmtime, reverse=True)
    if pr_reports:
        pr_reports.sort(key=os.path.getmtime, reverse=True)

    # Determine mode
    if jira_reports and pr_reports:
        mode = "combined"
    elif jira_reports or pr_reports:
        mode = "single"
    else:
        mode = "none"

    return {
        "mode": mode,
        "jira": jira_reports[0] if jira_reports else None,
        "pr": pr_reports[0] if pr_reports else None,
        "is_aggregated": is_aggregated,
    }


def extract_project_name_from_path(report_path: str) -> str:
    """Extract project name from report path."""
    parts = Path(report_path).parts
    for i, part in enumerate(parts):
        if part == "reports" and i + 1 < len(parts):
            return parts[i + 1].replace("-", " ").replace("_", " ").title()
    return "Unknown Project"


def create_combined_analysis_prompt(
    jira_report_path: str,
    pr_report_path: str,
    project_name: str = None,
    is_aggregated: bool = False,
    template_path: str = "config/combined_analysis_prompt_template.yaml",
) -> str:
    """
    Create a combined analysis prompt for JIRA + PR reports using template.

    Args:
        jira_report_path: Path to JIRA report
        pr_report_path: Path to PR report
        project_name: Project name (auto-detected if not provided)
        is_aggregated: True if analyzing aggregated multi-team reports
        template_path: Path to prompt template file

    Returns:
        Combined analysis prompt (English)
    """
    # Read reports
    jira_content = read_report_content(jira_report_path)
    pr_content = read_report_content(pr_report_path)

    # Auto-detect project name if not provided
    if not project_name:
        project_name = extract_project_name_from_path(jira_report_path)

    # Extract phase names from JIRA report
    try:
        preprocessor = ReportPreprocessor(jira_report_path)
        preprocessed_data = preprocessor.load_and_parse()
        phases = preprocessed_data.get("phases", [])
        phase_description = " / ".join(phases) if phases else "multiple phases"
    except Exception:
        # Fallback if preprocessing fails
        phase_description = "multiple phases"

    # Load template
    try:
        with open(template_path, "r", encoding="utf-8") as f:
            template = yaml.safe_load(f)
    except Exception as e:
        logger.warning(f"Failed to load template {template_path}: {e}. Using fallback.")
        template = None

    # Build prompt from template
    if template:
        # Get scope intro
        scope_variations = template.get("scope_variations", {})
        if is_aggregated:
            scope_template = scope_variations.get("aggregated", "")
        else:
            scope_template = scope_variations.get("single_team", "")
        scope_intro = scope_template.format(
            project_name=project_name, phase_description=phase_description
        )

        # Build prompt parts
        role = template.get("role", "").strip()
        intro = template.get("introduction", "").strip()
        intro = intro.format(scope_intro=scope_intro)

        # Build sections
        sections = template.get("sections", {})
        sections_text = []

        for section_key, section_data in sections.items():
            title = section_data.get("title", "")
            description = section_data.get("description", "")
            questions = section_data.get("questions", [])
            areas = section_data.get("areas", [])
            requirements = section_data.get("requirements", [])
            note = section_data.get("note", "")

            section_parts = [f"\n---\n\n## {title}"]

            # Add description if present
            if description:
                section_parts.append(f"\n{description}")

            # Add questions - use numbered list if multiple questions with question marks
            if questions:
                section_parts.append("")  # Add blank line before list
                # Use numbered list if we have multiple items that look like questions
                use_numbers = len(questions) > 1 and any("?" in q for q in questions)
                for i, q in enumerate(questions, 1):
                    prefix = f"{i}. " if use_numbers else "- "
                    section_parts.append(f"{prefix}{q}")

            # Add areas if present (for health_assessment section)
            if areas:
                section_parts.append("")  # Add blank line before list
                for area in areas:
                    section_parts.append(f"- {area}")

            # Add requirements if present (for recommendations section)
            if requirements:
                section_parts.append("")  # Add blank line before list
                for req in requirements:
                    section_parts.append(f"- {req}")

            # Add note if present (typically at the end)
            if note:
                section_parts.append(f"\n{note}")

            sections_text.append("\n".join(section_parts))

        # Build output format section
        output_format = template.get("output_format", {})
        output_text = []
        if output_format:
            output_text.append("\n---\n\n## Output Format Requirements")

            style = output_format.get("style", "")
            if style:
                output_text.append(f"\n**Style**: {style}")

            formatting = output_format.get("formatting", [])
            if formatting:
                output_text.append("\n**Formatting Guidelines**:")
                for rule in formatting:
                    output_text.append(f"- {rule}")

        output_format_section = "\n".join(output_text) if output_text else ""

        # Combine all parts with source report information
        jira_filename = Path(jira_report_path).name
        pr_filename = Path(pr_report_path).name

        prompt = f"""{role}

{intro}

Source Reports:
- JIRA Report: {jira_filename}
- PR Report: {pr_filename}

========================
【JIRA Metrics Report】
========================

```
{jira_content}
```

========================
【PR Metrics Report】
========================

```
{pr_content}
```

Please provide analysis following this structure (strictly):

{''.join(sections_text)}
{output_format_section}
"""
    else:
        # Fallback to simple prompt if template loading fails
        if is_aggregated:
            scope_intro = f"Below are two aggregated reports covering multiple teams/projects under 【{project_name}】 across {phase_description}"
        else:
            scope_intro = (
                f"Below are two reports from project 【{project_name}】 across {phase_description}"
            )

        jira_filename = Path(jira_report_path).name
        pr_filename = Path(pr_report_path).name

        prompt = f"""You are a senior AI analyst specializing in Engineering Productivity and Project Management.

{scope_intro}:

- JIRA Metrics Report: Reflects requirement flow, delivery rhythm, and process bottlenecks
- GitHub PR Metrics Report: Reflects development behavior, code changes, and collaboration patterns

These two reports MUST be analyzed TOGETHER, not separately.

Source Reports:
- JIRA Report: {jira_filename}
- PR Report: {pr_filename}

========================
【JIRA Metrics Report】
========================

```
{jira_content}
```

========================
【PR Metrics Report】
========================

```
{pr_content}
```

Please provide comprehensive analysis covering:
1. Overall Project Trends
2. JIRA × PR Cross-Analysis
3. AI Impact Assessment
4. Project Health
5. Actionable Recommendations
"""

    return prompt


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


def main():
    parser = argparse.ArgumentParser(
        description="Generate AI analysis prompts from reports (supports combined JIRA+PR analysis)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Combined analysis (directory with both JIRA + PR reports)
  python -m impactlens.scripts.generate_analysis_prompt \\
    --reports-dir "reports/team-name" \\
    --prompt-only

  # Single file analysis
  python -m impactlens.scripts.generate_analysis_prompt \\
    --reports-dir "reports/github/combined_pr_report_*.tsv" \\
    --prompt-only
        """,
    )

    from impactlens.utils.common_args import add_prompt_generation_args

    add_prompt_generation_args(parser)
    args = parser.parse_args()

    logger.info("=" * 80)
    logger.info("AI Report Analysis Prompt Generator")
    logger.info("=" * 80)
    logger.info("")

    # Smart detection: file or directory?
    input_path = Path(args.reports_dir)

    # Check if input is a directory or file pattern
    if input_path.exists() and input_path.is_dir():
        # Directory mode: auto-detect combined or single analysis
        logger.info(f"📁 Directory mode: {args.reports_dir}")
        logger.info("🔍 Searching for reports...")

        reports = find_reports_in_directory(args.reports_dir)

        if reports["mode"] == "none":
            logger.error("❌ No combined reports found in directory")
            logger.error("   Expected: combined_jira_report_*.tsv and/or combined_pr_report_*.tsv")
            return 1
        elif reports["mode"] == "combined":
            # Combined analysis mode
            logger.info("   ✓ Found JIRA + PR reports → Combined Analysis Mode")
            logger.info(f"   📊 JIRA: {Path(reports['jira']).name}")
            logger.info(f"   📊 PR: {Path(reports['pr']).name}")
            logger.info("")

            # Get project name
            project_name = extract_project_name_from_path(reports["jira"])
            logger.info(f"📋 Project: {project_name}")
            logger.info("")

            # Generate combined prompt
            logger.info("✨ Generating combined analysis prompt...")
            is_aggregated = reports.get("is_aggregated", False)
            if is_aggregated:
                logger.info("   ℹ️  Aggregated multi-team reports detected")
            prompt = create_combined_analysis_prompt(
                reports["jira"],
                reports["pr"],
                project_name=project_name,
                is_aggregated=is_aggregated,
            )

            # Use jira report path as reference for saving
            report_path = reports["jira"]
            is_combined = True

        else:
            # Single report mode
            report_path = reports["jira"] or reports["pr"]
            logger.info(f"   ✓ Found single report → Single Analysis Mode")
            logger.info(f"   📊 Report: {Path(report_path).name}")
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
            is_combined = False
    else:
        # File mode: original behavior (file path or glob pattern)
        logger.info(f"📄 File mode: {args.reports_dir}")
        report_path = find_latest_report(args.reports_dir)
        logger.info(f"   📊 Report: {Path(report_path).name}")
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
        is_combined = False

    # Display and save the prompt
    logger.info("")
    logger.info("=" * 80)
    logger.info("🎯 GENERATED ANALYSIS PROMPT")
    logger.info("=" * 80)
    logger.info("")
    print(prompt)
    logger.info("")

    # Save prompt to file
    output_dir_path = Path(args.output_dir)
    output_dir_path.mkdir(parents=True, exist_ok=True)

    # Use different filename for combined vs single analysis
    if is_combined:
        # Combined analysis: use project name
        project_name_safe = project_name.lower().replace(" ", "_")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        prompt_file = (
            output_dir_path / f"combined_analysis_prompt_{project_name_safe}_{timestamp}.txt"
        )
    else:
        # Single report analysis: use report name
        report_name = Path(report_path).name
        prompt_file = output_dir_path / f"analysis_prompt_{report_name.replace('.tsv', '.txt')}"

    with open(prompt_file, "w", encoding="utf-8") as f:
        f.write(prompt)

    logger.info(f"💾 Prompt saved to: {prompt_file}")
    logger.info("")
    logger.info("=" * 80)
    logger.info("📋 NEXT STEPS")
    logger.info("=" * 80)
    logger.info("")
    logger.info("To run Gemini analysis on this prompt:")
    logger.info(f"  python -m impactlens.scripts.analyze_with_gemini \\")
    logger.info(f'    --prompt-file "{prompt_file}" \\')
    logger.info(f'    --output-dir "{args.output_dir}"')
    logger.info("")
    return 0


if __name__ == "__main__":
    sys.exit(main())
