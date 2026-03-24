#!/usr/bin/env python3
"""
Test script for debugging Jira API queries locally.
Usage: python test_jira_api.py
"""

import os
import sys
import json
import base64
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from impactlens.clients.jira_client import JiraClient
from impactlens.utils.logger import logger
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)


def print_curl_command(jira_url, jql, email, api_token, max_results=50):
    """Generate and print a curl command for the API request."""
    url = f"{jira_url}/rest/api/3/search/jql"

    body = {
        "jql": jql,
        "fields": [
            "created",
            "resolutiondate",
            "status",
            "issuetype",
            "timeoriginalestimate",
            "timetracking",
        ],
        "maxResults": max_results,
    }

    # Masked version for display
    masked_token = api_token[:4] + "..." + api_token[-4:] if len(api_token) > 8 else "***"
    masked_email = email if email else "NO_EMAIL_SET"

    print("\n" + "━" * 80)
    print("📋 COPY & PASTE - CURL COMMAND")
    print("━" * 80)
    print(f"Auth: {masked_email} / {masked_token}")
    print()

    # Template version with placeholder
    curl_template = f"""curl --request POST \\
  --url '{url}' \\
  --user '{email}:<YOUR_API_TOKEN>' \\
  --header 'Accept: application/json' \\
  --header 'Content-Type: application/json' \\
  --data '{json.dumps(body)}'"""

    print(curl_template)
    print()

    # Print with real token for secure environments
    print("━" * 80)
    print("🔐 WITH REAL TOKEN (secure environment only)")
    print("━" * 80)
    real_curl = f"""curl --request POST \\
  --url '{url}' \\
  --user '{email}:{api_token}' \\
  --header 'Accept: application/json' \\
  --header 'Content-Type: application/json' \\
  --data '{json.dumps(body)}'"""
    print(real_curl)
    print()

    # Print request details separately
    print("━" * 80)
    print("📦 REQUEST DETAILS")
    print("━" * 80)
    print(f"Endpoint: {url}")
    print(f"Method: POST")
    print(f"Auth: Basic ({email}:{masked_token})")
    print(f"\nRequest Body:")
    print(json.dumps(body, indent=2))
    print("━" * 80)
    print()


def test_simple_query():
    """Test a simple JQL query."""
    print("=" * 80)
    print("TEST 1: Simple Query")
    print("=" * 80)

    client = JiraClient()

    # Simple query - just get recent issues from project
    jql = 'project = "KFLUXUI" AND resolved >= -7d'

    print(f"\nJQL: {jql}")
    print(f"Jira URL: {client.jira_url}")

    # Print curl command for this query
    if client.email and client.api_token:
        print_curl_command(client.jira_url, jql, client.email, client.api_token, max_results=50)

    result = client.fetch_jira_data(jql, max_results=50)

    if result:
        issues = result.get("issues", [])
        total = result.get("total", "N/A")  # total may not exist in API v3
        print(f"✓ Success!")
        print(f"  Issues returned: {len(issues)}")
        print(f"  Total (if available): {total}")
        if issues:
            print(f"  First issue: {issues[0]['key']}")
            print(f"  Last issue: {issues[-1]['key']}")
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
    jql = 'project = "KFLUXUI" AND assignee = "wlin@redhat.com" AND resolved >= -30d'

    print(f"\nJQL: {jql}")

    # Print curl command
    if client.email and client.api_token:
        print_curl_command(client.jira_url, jql, client.email, client.api_token, max_results=50)

    result = client.fetch_jira_data(jql, max_results=50)

    if result:
        issues = result.get("issues", [])
        print(f"✓ Email query works!")
        print(f"  Issues returned: {len(issues)}")
    else:
        print("✗ Email query failed")
        print("\n💡 Trying with username instead...")

        # Try with username (without @redhat.com)
        jql = 'project = "KFLUXUI" AND assignee = wlin AND resolved >= -30d'
        print(f"JQL: {jql}")
        result = client.fetch_jira_data(jql, max_results=50)

        if result:
            issues = result.get("issues", [])
            print(f"✓ Username query works!")
            print(f"  Issues returned: {len(issues)}")
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
        ("Negative days with quotes", 'resolved >= "-7d"'),
        ("Negative days without quotes", "resolved >= -7d"),
        ("Specific date", 'resolved >= "2024-12-01"'),
        ("StartOfDay function", "resolved >= startOfDay(-7d)"),
    ]

    for name, date_clause in date_formats:
        print(f"\n{name}: {date_clause}")
        jql = f'project = "KFLUXUI" AND {date_clause}'

        result = client.fetch_jira_data(jql, max_results=10)

        if result:
            issues = result.get("issues", [])
            print(f"  ✓ Works! Issues returned: {len(issues)}")
        else:
            print(f"  ✗ Failed")


def test_problematic_query():
    """Test the actual problematic query from the error log."""
    print("\n" + "=" * 80)
    print("TEST 4: Complex Query with Multiple Conditions")
    print("=" * 80)

    client = JiraClient()

    # Exact query from error log (simplified)
    jql = '''project = "KFLUXUI"
        AND (assignee = "wlin@redhat.com" OR assignee = "mtakac@redhat.com")
        AND resolved >= "-181d"
        AND resolved <= "-2d"'''

    print(f"\nJQL: {jql}")

    # Print curl command
    if client.email and client.api_token:
        print_curl_command(client.jira_url, jql, client.email, client.api_token, max_results=50)

    result = client.fetch_jira_data(jql, max_results=50)

    if result:
        issues = result.get("issues", [])
        print(f"✓ Success!")
        print(f"  Issues returned: {len(issues)}")
        return True
    else:
        print("✗ Failed - this is the problematic query")
        print("\n💡 Trying fixes...")

        # Fix 1: Remove quotes from dates
        jql_fix1 = """project = "KFLUXUI"
            AND (assignee = "wlin@redhat.com" OR assignee = "mtakac@redhat.com")
            AND resolved >= -181d
            AND resolved <= -2d"""

        print(f"\nFix 1 - Remove date quotes: {jql_fix1}")
        result = client.fetch_jira_data(jql_fix1, max_results=50)

        if result:
            issues = result.get("issues", [])
            print(f"  ✓ This works! Issues returned: {len(issues)}")
            return True
        else:
            print("  ✗ Still failing")

        # Fix 2: Use usernames instead of emails
        jql_fix2 = """project = "KFLUXUI"
            AND (assignee = wlin OR assignee = mtakac)
            AND resolved >= -181d
            AND resolved <= -2d"""

        print(f"\nFix 2 - Use usernames: {jql_fix2}")
        result = client.fetch_jira_data(jql_fix2, max_results=50)

        if result:
            issues = result.get("issues", [])
            print(f"  ✓ This works! Issues returned: {len(issues)}")
            return True
        else:
            print("  ✗ Still failing")

    return False


def test_pagination():
    """Test pagination with token-based approach."""
    print("\n" + "=" * 80)
    print("TEST 5: Pagination (Token-based)")
    print("=" * 80)

    client = JiraClient()

    jql = 'project = "KFLUXUI" AND resolved >= -90d'

    print(f"\nJQL: {jql}")
    print(f"Fetching all issues with pagination...\n")

    all_issues = client.fetch_all_issues(jql, batch_size=10)

    print(f"\n✓ Pagination test complete!")
    print(f"  Total issues fetched: {len(all_issues)}")
    if all_issues:
        print(f"  First issue: {all_issues[0]['key']}")
        print(f"  Last issue: {all_issues[-1]['key']}")

    return True


def main():
    """Run all tests."""
    print("\n" + "🔍 JIRA API DEBUG TESTER (API v3)")
    print("=" * 80)

    # Check environment
    missing_vars = []
    if not os.getenv("JIRA_API_TOKEN"):
        missing_vars.append("JIRA_API_TOKEN")
    if not os.getenv("JIRA_EMAIL"):
        missing_vars.append("JIRA_EMAIL")

    if missing_vars:
        print("⚠️  Warning: Missing environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nSet them with:")
        print("   export JIRA_EMAIL='your-email@redhat.com'")
        print("   export JIRA_API_TOKEN='your-token'")
        print("   export JIRA_URL='https://redhat.atlassian.net'  # optional")
        print()
        return 1

    # Run tests
    results = []

    try:
        results.append(("Simple query", test_simple_query()))
        results.append(("Assignee email", test_assignee_email()))
        test_date_formats()
        results.append(("Complex query", test_problematic_query()))
        results.append(("Pagination", test_pagination()))
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
