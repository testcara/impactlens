#!/usr/bin/env python3
"""
Test script for debugging Jira API queries locally.
Usage: python test_jira_api.py
"""

import os
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from impactlens.clients.jira_client import JiraClient
from impactlens.utils.logger import logger
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)


def test_simple_query():
    """Test a simple JQL query."""
    print("=" * 80)
    print("TEST 1: Simple Query")
    print("=" * 80)

    client = JiraClient()

    # Simple query - just get recent issues from project
    jql = 'project = "Konflux Release" AND resolved >= -7d'

    print(f"\nJQL: {jql}")
    print(f"Jira URL: {client.jira_url}")
    print()

    result = client.fetch_jira_data(jql, max_results=1)

    if result:
        print(f"✓ Success! Total issues: {result.get('total', 0)}")
        if result.get('issues'):
            issue = result['issues'][0]
            print(f"  Example issue: {issue['key']}")
    else:
        print("✗ Failed - see error above")

    return result is not None


def test_assignee_email():
    """Test querying by assignee email."""
    print("\n" + "=" * 80)
    print("TEST 2: Assignee by Email")
    print("=" * 80)

    client = JiraClient()

    # Try with email
    jql = 'project = "Konflux Release" AND assignee = "damoreno@redhat.com" AND resolved >= -30d'

    print(f"\nJQL: {jql}")
    print()

    result = client.fetch_jira_data(jql, max_results=1)

    if result:
        print(f"✓ Email query works! Total: {result.get('total', 0)}")
    else:
        print("✗ Email query failed")
        print("\n💡 Trying with username instead...")

        # Try with username (without @redhat.com)
        jql = 'project = "Konflux Release" AND assignee = damoreno AND resolved >= -30d'
        print(f"JQL: {jql}")
        result = client.fetch_jira_data(jql, max_results=1)

        if result:
            print(f"✓ Username query works! Total: {result.get('total', 0)}")
        else:
            print("✗ Username query also failed")

    return result is not None


def test_date_formats():
    """Test different date formats."""
    print("\n" + "=" * 80)
    print("TEST 3: Date Format Variations")
    print("=" * 80)

    client = JiraClient()

    date_formats = [
        ('Negative days with quotes', 'resolved >= "-7d"'),
        ('Negative days without quotes', 'resolved >= -7d'),
        ('Specific date', 'resolved >= "2024-12-01"'),
        ('StartOfDay function', 'resolved >= startOfDay(-7d)'),
    ]

    for name, date_clause in date_formats:
        print(f"\n{name}: {date_clause}")
        jql = f'project = "Konflux Release" AND {date_clause}'

        result = client.fetch_jira_data(jql, max_results=1)

        if result:
            print(f"  ✓ Works! Total: {result.get('total', 0)}")
        else:
            print(f"  ✗ Failed")


def test_problematic_query():
    """Test the actual problematic query from the error log."""
    print("\n" + "=" * 80)
    print("TEST 4: Reproduce Original Error")
    print("=" * 80)

    client = JiraClient()

    # Exact query from error log (simplified)
    jql = '''project = "Konflux Release"
        AND (assignee = "damoreno@redhat.com" OR assignee = "elgerman@redhat.com")
        AND resolved >= "-181d"
        AND resolved <= "-2d"'''

    print(f"\nJQL: {jql}")
    print()

    result = client.fetch_jira_data(jql, max_results=1)

    if result:
        print(f"✓ Success! Total: {result.get('total', 0)}")
    else:
        print("✗ Failed - this is the problematic query")
        print("\n💡 Trying fixes...")

        # Fix 1: Remove quotes from dates
        jql_fix1 = '''project = "Konflux Release"
            AND (assignee = "damoreno@redhat.com" OR assignee = "elgerman@redhat.com")
            AND resolved >= -181d
            AND resolved <= -2d'''

        print(f"\nFix 1 - Remove date quotes: {jql_fix1}")
        result = client.fetch_jira_data(jql_fix1, max_results=1)

        if result:
            print(f"  ✓ This works! Total: {result.get('total', 0)}")
            return True
        else:
            print("  ✗ Still failing")

        # Fix 2: Use usernames instead of emails
        jql_fix2 = '''project = "Konflux Release"
            AND (assignee = damoreno OR assignee = elgerman)
            AND resolved >= -181d
            AND resolved <= -2d'''

        print(f"\nFix 2 - Use usernames: {jql_fix2}")
        result = client.fetch_jira_data(jql_fix2, max_results=1)

        if result:
            print(f"  ✓ This works! Total: {result.get('total', 0)}")
            return True
        else:
            print("  ✗ Still failing")

    return False


def main():
    """Run all tests."""
    print("\n" + "🔍 JIRA API DEBUG TESTER")
    print("=" * 80)

    # Check environment
    if not os.getenv("JIRA_API_TOKEN"):
        print("⚠️  Warning: JIRA_API_TOKEN not set")
        print("   Set it with: export JIRA_API_TOKEN='your-token'")
        print()

    # Run tests
    results = []

    try:
        results.append(("Simple query", test_simple_query()))
        results.append(("Assignee email", test_assignee_email()))
        test_date_formats()
        results.append(("Problematic query", test_problematic_query()))
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()

    # Summary
    print("\n" + "=" * 80)
    print("📊 TEST SUMMARY")
    print("=" * 80)

    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")

    print("\n" + "=" * 80)

    return 0 if all(r[1] for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
