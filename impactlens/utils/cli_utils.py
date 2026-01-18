"""
CLI utility functions for command-line scripts.

This module provides common functions used across different CLI scripts
to avoid code duplication and ensure consistent behavior.
"""

from datetime import datetime
from typing import Tuple


def parse_leave_days_capacity(args) -> Tuple[float, float]:
    """
    Parse leave_days and capacity from command line arguments.

    Args:
        args: Parsed argparse arguments with leave_days and capacity attributes

    Returns:
        Tuple of (leave_days, capacity)

    Raises:
        ValueError: If values cannot be converted to float
        SystemExit: If invalid values are provided (exits with code 1)

    Examples:
        >>> args = argparse.Namespace(leave_days='5', capacity='0.8')
        >>> leave_days, capacity = parse_leave_days_capacity(args)
        >>> print(leave_days, capacity)
        5.0 0.8
    """
    # Get leave_days from command line argument
    leave_days = 0.0
    if hasattr(args, "leave_days") and args.leave_days is not None:
        try:
            leave_days = float(args.leave_days)
        except ValueError:
            print(f"Error: --leave-days must be a number, got '{args.leave_days}'")
            raise SystemExit(1)

    # Get capacity from command line argument
    capacity = 1.0
    if hasattr(args, "capacity") and args.capacity is not None:
        try:
            capacity = float(args.capacity)
        except ValueError:
            print(f"Error: --capacity must be a number, got '{args.capacity}'")
            raise SystemExit(1)

    return leave_days, capacity


def validate_date_range(start_date: str, end_date: str) -> bool:
    """
    Validate date range format (YYYY-MM-DD).

    Args:
        start_date: Start date string
        end_date: End date string

    Returns:
        True if dates are valid

    Raises:
        SystemExit: If dates are invalid (exits with code 1)

    Examples:
        >>> validate_date_range("2024-01-01", "2024-03-31")
        True
        >>> validate_date_range("2024-1-1", "2024-03-31")  # Invalid format
        SystemExit: 1
    """
    try:
        datetime.strptime(start_date, "%Y-%m-%d")
        datetime.strptime(end_date, "%Y-%m-%d")
        return True
    except ValueError:
        print("Error: Dates must be in YYYY-MM-DD format")
        raise SystemExit(1)


def print_step(message: str, emoji: str = "📊"):
    """
    Print a step message with emoji prefix.

    Args:
        message: Message to print
        emoji: Emoji prefix (default: 📊)

    Examples:
        >>> print_step("Collecting data...")
        📊 Collecting data...
        >>> print_step("Done", emoji="✓")
        ✓ Done
    """
    print(f"\n{emoji} {message}")


def print_success(message: str):
    """
    Print a success message with checkmark.

    Args:
        message: Success message to print

    Examples:
        >>> print_success("Report generated successfully")
        ✓ Report generated successfully
    """
    print(f"✓ {message}")


def print_error(message: str):
    """
    Print an error message with cross mark.

    Args:
        message: Error message to print

    Examples:
        >>> print_error("File not found")
        ✗ File not found
    """
    print(f"✗ {message}")
