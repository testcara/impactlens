"""
Anonymization utilities for protecting individual privacy in reports.

This module provides functions to anonymize individual names in combined reports
while maintaining consistency across the report.
"""

import hashlib
import os
from typing import Dict, List


class NameAnonymizer:
    """Anonymizes individual names to protect privacy using consistent hash-based IDs."""

    def __init__(self):
        """Initialize the anonymizer with an empty name mapping."""
        self._name_map: Dict[str, str] = {}

    def _generate_hash_id(self, name: str) -> str:
        """
        Generate a consistent hash-based ID for a name.

        Args:
            name: The name to hash

        Returns:
            A short hash ID (e.g., "A3F2", "B7E1")
        """
        # Create SHA256 hash of the name
        hash_obj = hashlib.sha256(name.encode("utf-8"))
        hash_hex = hash_obj.hexdigest()

        # Take first 4 characters and make uppercase for readability
        short_hash = hash_hex[:4].upper()

        return short_hash

    def anonymize(self, name: str) -> str:
        """
        Anonymize a name to a consistent hash-based anonymous ID.

        Args:
            name: The real name to anonymize

        Returns:
            Anonymous ID (e.g., "Developer-A3F2", "Developer-B7E1")
            Same name always produces same ID across different runs.
        """
        if not name or name.lower() in ["general", "team", ""]:
            # Don't anonymize team-level or empty names
            return name

        # Return existing mapping if already anonymized
        if name in self._name_map:
            return self._name_map[name]

        # Create hash-based anonymous ID
        hash_id = self._generate_hash_id(name)
        anonymous_id = f"Developer-{hash_id}"
        self._name_map[name] = anonymous_id
        return anonymous_id

    def anonymize_email(self, email: str) -> str:
        """
        Anonymize an email address.

        Args:
            email: The email address to anonymize

        Returns:
            Anonymized email (e.g., "developer-1@anonymous.local")
        """
        if not email or "@" not in email:
            return email

        # Extract username part before @
        username = email.split("@")[0]

        # Anonymize the username
        anonymous_id = self.anonymize(username)

        # Return anonymized email
        return f"{anonymous_id.lower()}@anonymous.local"

    def get_mapping(self) -> Dict[str, str]:
        """
        Get the current name mapping.

        Returns:
            Dictionary mapping real names to anonymous IDs
        """
        return self._name_map.copy()

    def clear(self):
        """Clear all anonymization mappings."""
        self._name_map.clear()
        self._counter = 0


def anonymize_names_in_list(names: List[str], anonymizer: NameAnonymizer = None) -> List[str]:
    """
    Anonymize a list of names.

    Args:
        names: List of names to anonymize
        anonymizer: Optional NameAnonymizer instance (creates new one if None)

    Returns:
        List of anonymized names
    """
    if anonymizer is None:
        anonymizer = NameAnonymizer()

    return [anonymizer.anonymize(name) for name in names]


def anonymize_member_data(
    member_name: str, member_email: str = None, anonymizer: NameAnonymizer = None
) -> tuple[str, str]:
    """
    Anonymize both member name and email.

    Args:
        member_name: The member's name
        member_email: The member's email (optional)
        anonymizer: Optional NameAnonymizer instance

    Returns:
        Tuple of (anonymized_name, anonymized_email)
    """
    if anonymizer is None:
        anonymizer = NameAnonymizer()

    anon_name = anonymizer.anonymize(member_name)
    anon_email = anonymizer.anonymize_email(member_email) if member_email else ""

    return anon_name, anon_email


def get_display_member_info(
    member_name: str,
    member_email: str = None,
    hide_individual_names: bool = False,
    anonymizer: NameAnonymizer = None,
) -> dict:
    """
    Get display member information with optional anonymization.

    This is the main utility function for report generation scripts.
    Use this to consistently handle member information across all reports.

    Args:
        member_name: The member's real name
        member_email: The member's email (optional)
        hide_individual_names: Whether to anonymize the information
        anonymizer: Optional NameAnonymizer instance (will create if needed)

    Returns:
        Dictionary with display_name and display_email keys

    Example:
        >>> info = get_display_member_info("alice", "alice@example.com", hide_individual_names=True)
        >>> print(info['display_name'])
        'Developer-2BD8'
        >>> print(info['display_email'])
        'developer-2bd8@anonymous.local'
    """
    if hide_individual_names:
        if anonymizer is None:
            anonymizer = NameAnonymizer()

        display_name = anonymizer.anonymize(member_name)
        display_email = anonymizer.anonymize_email(member_email) if member_email else ""
    else:
        display_name = member_name
        display_email = member_email if member_email else ""

    return {"display_name": display_name, "display_email": display_email}


def should_include_sensitive_fields(hide_individual_names: bool) -> bool:
    """
    Determine whether to include sensitive fields in combined reports.

    Sensitive fields include:
    - leave_days
    - capacity
    - Any other personal information that could identify individuals

    Args:
        hide_individual_names: Whether individual names are being hidden

    Returns:
        True if sensitive fields should be included, False otherwise

    Example:
        >>> if should_include_sensitive_fields(hide_individual_names):
        >>>     # Include leave_days and capacity
        >>> else:
        >>>     # Skip sensitive fields
    """
    return not hide_individual_names


# Global anonymizer instance for consistent anonymization across the application
_global_anonymizer = NameAnonymizer()


def anonymize_name(name: str) -> str:
    """
    Convenience function to anonymize a single name using the global anonymizer.

    This ensures consistent anonymization across the entire application session.

    Args:
        name: The name to anonymize (can be username, email, etc.)

    Returns:
        Anonymized name (e.g., "Developer-A3F2")

    Example:
        >>> anonymize_name("alice")
        'Developer-2BD8'
        >>> anonymize_name("alice@example.com")
        'Developer-27D8'
    """
    return _global_anonymizer.anonymize(name)
