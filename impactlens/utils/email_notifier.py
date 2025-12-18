"""
Email notification utilities for sharing anonymized identifiers with team members.

This module provides functionality to send email notifications to team members
when their data is included in anonymized reports, informing them of their
anonymous identifier (hash code) so they can choose to share it if desired.
"""

import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional
from datetime import datetime


class EmailNotifier:
    """Sends email notifications to team members about their anonymous identifiers."""

    def __init__(
        self,
        smtp_host: str = None,
        smtp_port: int = None,
        smtp_user: str = None,
        smtp_password: str = None,
        from_email: str = None,
    ):
        """
        Initialize the email notifier.

        If no parameters provided, automatically loads from environment variables
        using centralized SMTP configuration.

        Args:
            smtp_host: SMTP server hostname (defaults to env SMTP_HOST or 'smtp.gmail.com')
            smtp_port: SMTP server port (defaults to env SMTP_PORT or 587)
            smtp_user: SMTP username (defaults to env SMTP_USER or MAIL_APP_USER)
            smtp_password: SMTP password (defaults to env SMTP_PASSWORD or MAIL_APP_PASSWORD)
            from_email: Sender email address (defaults to env FROM_EMAIL or 'ImpactLens <user>')
        """
        # Use centralized config if no explicit values provided
        if all(v is None for v in [smtp_host, smtp_port, smtp_user, smtp_password, from_email]):
            from impactlens.utils.smtp_config import get_smtp_config
            config = get_smtp_config()
            self.smtp_host = config["smtp_host"]
            self.smtp_port = config["smtp_port"]
            self.smtp_user = config["smtp_user"]
            self.smtp_password = config["smtp_password"]
            self.from_email = config["from_email"]
        else:
            # Allow explicit override (for backward compatibility)
            self.smtp_host = smtp_host or os.getenv("SMTP_HOST", "localhost")
            self.smtp_port = smtp_port or int(os.getenv("SMTP_PORT", "587"))
            self.smtp_user = smtp_user or os.getenv("SMTP_USER")
            self.smtp_password = smtp_password or os.getenv("SMTP_PASSWORD")
            self.from_email = from_email or os.getenv("FROM_EMAIL", "impactlens@localhost")

    def _create_email_body(
        self,
        member_name: str,
        anonymous_id: str,
        pr_url: Optional[str] = None,
        report_context: Optional[str] = None,
    ) -> str:
        """
        Create the email body content.

        Args:
            member_name: The team member's real name
            anonymous_id: Their anonymous identifier (e.g., "Developer-A3F2")
            pr_url: Optional PR URL that triggered the report
            report_context: Optional additional context about the report

        Returns:
            Email body as HTML string
        """
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

        # Build trigger info
        trigger_info = ""
        if pr_url:
            trigger_info = f"- Triggered by: <a href='{pr_url}'>Pull Request</a><br>"
        elif report_context:
            trigger_info = f"- Context: {report_context}<br>"

        html = f"""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <h2 style="color: #2563eb;">🔒 ImpactLens Report - Your Anonymous Identifier</h2>

    <p>Hi,</p>

    <p>ImpactLens has generated a team performance report that includes your contributions.</p>

    <div style="background-color: #f3f4f6; padding: 15px; border-left: 4px solid #2563eb; margin: 20px 0;">
        <strong>Report Details:</strong><br>
        {trigger_info}
        - Generated at: {timestamp}
    </div>

    <p><strong>To protect your privacy</strong>, individual names have been anonymized in the report.</p>

    <div style="background-color: #fef3c7; padding: 15px; border-left: 4px solid #f59e0b; margin: 20px 0;">
        <strong>Your anonymous identifier in this report is:</strong><br>
        <span style="font-size: 18px; font-weight: bold; color: #f59e0b;">{anonymous_id}</span>
    </div>

    <h3 style="color: #059669;">You Are In Control</h3>
    <p>
        You can choose to share this identifier with your manager or team lead if you wish.
        <strong>This is entirely your decision</strong> - the report will not reveal your identity otherwise.
    </p>

    <p>
        This feature exists to give you control over your privacy while allowing you the option
        to connect your work to your identity if you choose to do so.
    </p>

    <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 30px 0;">

    <p style="color: #6b7280; font-size: 12px;">
        This is an automated message from ImpactLens<br>
        <a href="https://github.com/testcara/impactlens" style="color: #2563eb;">Learn more about ImpactLens</a>
    </p>
</body>
</html>
"""
        return html

    def send_notification(
        self,
        to_email: str,
        member_name: str,
        anonymous_id: str,
        pr_url: Optional[str] = None,
        report_context: Optional[str] = None,
        dry_run: bool = False,
    ) -> bool:
        """
        Send email notification to a team member.

        Args:
            to_email: Recipient email address
            member_name: Team member's real name
            anonymous_id: Their anonymous identifier
            pr_url: Optional PR URL that triggered the report
            report_context: Optional additional context
            dry_run: If True, print email instead of sending

        Returns:
            True if email was sent successfully, False otherwise
        """
        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = "ImpactLens Report - Your Anonymous Identifier"
            msg["From"] = self.from_email
            msg["To"] = to_email

            # Create HTML content
            html_content = self._create_email_body(
                member_name, anonymous_id, pr_url, report_context
            )

            # Attach HTML content
            html_part = MIMEText(html_content, "html")
            msg.attach(html_part)

            if dry_run:
                print(f"\n{'='*60}")
                print(f"DRY RUN - Email that would be sent:")
                print(f"{'='*60}")
                print(f"To: {to_email}")
                print(f"From: {self.from_email}")
                print(f"Subject: {msg['Subject']}")
                print(f"\n{html_content}")
                print(f"{'='*60}\n")
                return True

            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                if self.smtp_user and self.smtp_password:
                    server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)

            print(f"✓ Email notification sent to {to_email} (ID: {anonymous_id})")
            return True

        except Exception as e:
            print(f"✗ Failed to send email to {to_email}: {e}")
            return False

    def send_batch_notifications(
        self,
        name_mapping: Dict[str, str],
        email_mapping: Dict[str, str],
        pr_url: Optional[str] = None,
        report_context: Optional[str] = None,
        dry_run: bool = False,
    ) -> Dict[str, bool]:
        """
        Send email notifications to multiple team members.

        Args:
            name_mapping: Dict mapping real names to anonymous IDs
            email_mapping: Dict mapping real names to email addresses
            pr_url: Optional PR URL that triggered the report
            report_context: Optional additional context
            dry_run: If True, print emails instead of sending

        Returns:
            Dict mapping email addresses to success status
        """
        results = {}

        print(f"\n{'='*60}")
        print(f"Sending anonymized identifier notifications to {len(email_mapping)} team members...")
        print(f"{'='*60}\n")

        for member_name, email in email_mapping.items():
            if not email or email.lower() == "general" or "@" not in email:
                print(f"⊘ Skipping {member_name}: No valid email address")
                continue

            anonymous_id = name_mapping.get(member_name)
            if not anonymous_id:
                print(f"⊘ Skipping {member_name}: No anonymous ID found")
                continue

            success = self.send_notification(
                to_email=email,
                member_name=member_name,
                anonymous_id=anonymous_id,
                pr_url=pr_url,
                report_context=report_context,
                dry_run=dry_run,
            )
            results[email] = success

        # Summary
        success_count = sum(1 for v in results.values() if v)
        print(f"\n{'='*60}")
        print(f"Email notification summary: {success_count}/{len(results)} sent successfully")
        print(f"{'='*60}\n")

        return results


def notify_team_members(
    anonymizer,
    team_members: List[Dict],
    pr_url: Optional[str] = None,
    report_context: Optional[str] = None,
    dry_run: bool = False,
) -> Dict[str, bool]:
    """
    Convenience function to notify team members about their anonymous identifiers.

    Args:
        anonymizer: NameAnonymizer instance with the name mappings
        team_members: List of team member dicts with 'name' or 'member' and 'email' keys
        pr_url: Optional PR URL that triggered the report
        report_context: Optional additional context
        dry_run: If True, print emails instead of sending

    Returns:
        Dict mapping email addresses to success status

    Example:
        >>> from impactlens.utils.anonymization import NameAnonymizer
        >>> anonymizer = NameAnonymizer()
        >>> anonymizer.anonymize("alice")
        >>> team_members = [
        ...     {"member": "alice", "email": "alice@example.com"},
        ...     {"member": "bob", "email": "bob@example.com"}
        ... ]
        >>> results = notify_team_members(
        ...     anonymizer,
        ...     team_members,
        ...     pr_url="https://github.com/org/repo/pull/123",
        ...     dry_run=True
        ... )
    """
    # Build email mapping from team members
    email_mapping = {}
    for member in team_members:
        name = member.get("member") or member.get("name")
        email = member.get("email")
        if name and email:
            email_mapping[name] = email

    # Get name mapping from anonymizer
    name_mapping = anonymizer.get_mapping()

    # Send notifications using centralized SMTP configuration
    from impactlens.utils.smtp_config import create_email_notifier

    notifier = create_email_notifier()
    return notifier.send_batch_notifications(
        name_mapping=name_mapping,
        email_mapping=email_mapping,
        pr_url=pr_url,
        report_context=report_context,
        dry_run=dry_run,
    )
