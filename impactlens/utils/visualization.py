"""
Visualization Utilities

This module provides functions for generating box plot visualizations
for PR/Jira metrics comparison across different phases.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import matplotlib.pyplot as plt
import seaborn as sns
from impactlens.utils.logger import logger


# Set seaborn style for better-looking plots
sns.set_style("whitegrid")
sns.set_palette("Set2")


def extract_pr_data_from_json(json_files: List[Path], metric_key: str) -> List[float]:
    """
    Extract metric values from PR JSON report files.

    Args:
        json_files: List of PR metrics JSON file paths
        metric_key: Key to extract (e.g., 'time_to_merge_hours', 'time_to_first_review_hours')

    Returns:
        List of metric values
    """
    values = []
    for json_file in json_files:
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
                prs = data.get('prs', [])
                for pr in prs:
                    value = pr.get(metric_key)
                    if value is not None and value != 'N/A':
                        values.append(float(value))
        except Exception as e:
            logger.warning(f"Failed to extract {metric_key} from {json_file}: {e}")

    return values


def generate_boxplot(
    data_groups: Dict[str, List[float]],
    metric_name: str,
    metric_unit: str,
    output_path: Path,
    title: Optional[str] = None,
    figsize: Tuple[int, int] = (10, 6)
) -> Path:
    """
    Generate a box plot comparing multiple groups.

    Args:
        data_groups: Dictionary mapping group names to value lists
                     e.g., {'No AI': [1.2, 3.4, ...], 'With AI': [0.8, 2.1, ...]}
        metric_name: Name of the metric being plotted
        metric_unit: Unit of measurement (e.g., 'hours', 'days', 'count')
        output_path: Path to save the plot image
        title: Optional custom title
        figsize: Figure size (width, height)

    Returns:
        Path to the generated plot image
    """
    # Prepare data for seaborn
    plot_data = []
    for group_name, values in data_groups.items():
        for value in values:
            plot_data.append({'Group': group_name, 'Value': value})

    if not plot_data:
        logger.warning(f"No data to plot for {metric_name}")
        return None

    # Create figure
    fig, ax = plt.subplots(figsize=figsize)

    # Create box plot
    import pandas as pd
    df = pd.DataFrame(plot_data)
    sns.boxplot(data=df, x='Group', y='Value', ax=ax)

    # Add individual points with jitter
    sns.stripplot(data=df, x='Group', y='Value', ax=ax,
                  color='black', alpha=0.3, size=3)

    # Set labels and title
    ax.set_ylabel(f'{metric_name} ({metric_unit})', fontsize=12)
    ax.set_xlabel('Phase', fontsize=12)
    if title:
        ax.set_title(title, fontsize=14, fontweight='bold')
    else:
        ax.set_title(f'{metric_name} Comparison', fontsize=14, fontweight='bold')

    # Add grid
    ax.grid(axis='y', alpha=0.3)

    # Rotate x-axis labels if needed
    if len(data_groups) > 3:
        plt.xticks(rotation=15, ha='right')

    # Tight layout
    plt.tight_layout()

    # Save figure
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()

    logger.info(f"Box plot saved to {output_path}")
    return output_path
