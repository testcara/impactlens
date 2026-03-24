#!/usr/bin/env python3
"""
Manual test script for GitHub and GitLab GraphQL clients.

Usage:
    # Test GitHub (Recommended - using new GIT_* variables)
    export GIT_URL="https://github.com"
    export GITHUB_TOKEN="ghp_xxx"  # or GIT_TOKEN
    export GIT_REPO_OWNER="redhat-appstudio"
    export GIT_REPO_NAME="konflux-ui"
    python tests/manual/test_github_gitlab_client.py --platform github --start 2024-01-01 --end 2024-01-31

    # Test GitHub (Legacy - still supported)
    export GITHUB_URL="https://github.com"
    export GITHUB_TOKEN="ghp_xxx"
    export GITHUB_REPO_OWNER="redhat-appstudio"
    export GITHUB_REPO_NAME="konflux-ui"
    python tests/manual/test_github_gitlab_client.py --platform github --start 2024-01-01 --end 2024-01-31

    # Test GitLab (Recommended - using new GIT_* variables)
    export GIT_URL="https://gitlab.com"
    export GITLAB_TOKEN="glpat-xxx"  # or GIT_TOKEN
    export GIT_REPO_OWNER="gitlab-org"
    export GIT_REPO_NAME="gitlab"
    python tests/manual/test_github_gitlab_client.py --platform gitlab --start 2024-01-01 --end 2024-01-31

    # Test GitLab with self-signed certificate (disable SSL verification)
    export GIT_URL="https://gitlab.internal.company.com"
    export GIT_VERIFY_SSL="false"
    export GITLAB_TOKEN="glpat-xxx"
    export GIT_REPO_OWNER="myorg"
    export GIT_REPO_NAME="myrepo"
    python tests/manual/test_github_gitlab_client.py --platform gitlab --start 2024-01-01 --end 2024-01-31
"""

import sys
import os
import json
import argparse
from pathlib import Path
from datetime import datetime

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from impactlens.clients.github_client_graphql import GitGraphQLClient
from impactlens.utils.logger import logger
import logging

# Enable debug logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


def print_section(title):
    """Print a section header."""
    print("\n" + "━" * 80)
    print(f"  {title}")
    print("━" * 80)


def test_connection(client):
    """Test basic connection to GitHub/GitLab."""
    print_section("TEST 1: Connection Test")

    platform = "GitLab" if client.is_gitlab else "GitHub"
    print(f"\n✓ Connected to {platform}")
    print(f"  URL: {client.graphql_url}")
    print(f"  Repository: {client.repo_owner}/{client.repo_name}")
    print(f"  Cache directory: {client.cache_dir}")

    return True


def test_graphql_query(client):
    """Test GraphQL query construction."""
    print_section("TEST 2: GraphQL Query")

    query = client._build_graphql_query()

    print("\n📋 Generated GraphQL Query:")
    print("─" * 80)
    print(query[:500] + "..." if len(query) > 500 else query)
    print("─" * 80)

    # Check if query contains platform-specific keywords
    if client.is_gitlab:
        required_keywords = ["mergeRequests", "iid", "username", "diffStatsSummary"]
    else:
        required_keywords = ["pullRequests", "number", "login", "additions"]

    missing = [kw for kw in required_keywords if kw not in query]

    if missing:
        print(f"\n✗ Missing keywords: {missing}")
        return False
    else:
        print(f"\n✓ Query contains all required keywords")
        return True


def test_fetch_prs(client, start_date, end_date, author=None, max_prs=5):
    """Test fetching PRs/MRs."""
    print_section(f"TEST 3: Fetch PRs/MRs ({start_date} to {end_date})")

    if author:
        print(f"\nFiltering by author: {author}")

    print(f"\nFetching up to {max_prs} PRs/MRs...")
    print("(This may take a while depending on repository activity)")

    try:
        # Fetch without cache to test fresh request
        prs = client.fetch_merged_prs_graphql(
            start_date=start_date, end_date=end_date, author=author, use_cache=False
        )

        print(f"\n✓ Successfully fetched {len(prs)} PRs/MRs")

        if not prs:
            print("\n⚠️  No PRs/MRs found in date range")
            print("   Try expanding the date range or checking the repository has merged PRs")
            return True  # Not an error, just no data

        # Show first few PRs
        print(f"\n📊 Sample PRs/MRs (showing first {min(max_prs, len(prs))}):")
        print("─" * 80)

        for i, pr in enumerate(prs[:max_prs], 1):
            pr_type = "MR" if client.is_gitlab else "PR"
            print(f"\n{i}. {pr_type} #{pr['pr_number']}: {pr['title'][:60]}...")
            print(f"   Author: {pr['author']}")
            print(f"   Merged: {pr['merged_at']}")
            print(f"   URL: {pr['url']}")
            print(f"   Changes: +{pr['additions']} -{pr['deletions']} files:{pr['changed_files']}")
            print(
                f"   AI Assistance: {'Yes' if pr['has_ai_assistance'] else 'No'} "
                f"({pr['ai_percentage']:.1f}% commits)"
            )
            print(
                f"   Reviews: {pr['approvals_count']} approvals, "
                f"{pr['human_reviewers_count']} human reviewers"
            )
            print(f"   Comments: {pr['human_total_comments_count']} human comments")

        return True

    except Exception as e:
        print(f"\n✗ Error fetching PRs: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_pr_metrics(client, start_date, end_date):
    """Test that all expected metrics are present."""
    print_section("TEST 4: PR/MR Metrics Validation")

    print("\nFetching a single PR/MR to validate metrics...")

    try:
        prs = client.fetch_merged_prs_graphql(
            start_date=start_date, end_date=end_date, use_cache=False
        )

        if not prs:
            print("\n⚠️  No PRs/MRs to validate")
            return True

        pr = prs[0]

        # Expected metrics
        expected_fields = [
            "pr_number",
            "title",
            "author",
            "created_at",
            "merged_at",
            "url",
            "has_ai_assistance",
            "ai_tools",
            "ai_commits_count",
            "total_commits",
            "ai_percentage",
            "time_to_merge_hours",
            "time_to_merge_days",
            "changes_requested_count",
            "approvals_count",
            "reviewers_count",
            "reviewers",
            "human_reviewers_count",
            "human_reviewers",
            "review_comments_count",
            "issue_comments_count",
            "total_comments_count",
            "substantive_comments_count",
            "human_total_comments_count",
            "additions",
            "deletions",
            "changed_files",
        ]

        missing_fields = [field for field in expected_fields if field not in pr]

        if missing_fields:
            print(f"\n✗ Missing fields: {missing_fields}")
            return False
        else:
            print(f"\n✓ All {len(expected_fields)} expected fields present")

            # Show sample data
            print("\n📊 Sample metrics:")
            print(json.dumps({k: pr[k] for k in list(pr.keys())[:10]}, indent=2))

            return True

    except Exception as e:
        print(f"\n✗ Error validating metrics: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_cache(client, start_date, end_date):
    """Test caching functionality."""
    print_section("TEST 5: Cache Test")

    print("\nTesting cache functionality...")

    try:
        # Clear cache first
        client.clear_cache()
        print("✓ Cache cleared")

        # First fetch (should hit API)
        print("\nFirst fetch (from API)...")
        import time

        start_time = time.time()
        prs1 = client.fetch_merged_prs_graphql(
            start_date=start_date, end_date=end_date, use_cache=True
        )
        time1 = time.time() - start_time
        print(f"✓ Fetched {len(prs1)} PRs in {time1:.2f} seconds")

        # Second fetch (should hit cache)
        print("\nSecond fetch (from cache)...")
        start_time = time.time()
        prs2 = client.fetch_merged_prs_graphql(
            start_date=start_date, end_date=end_date, use_cache=True
        )
        time2 = time.time() - start_time
        print(f"✓ Fetched {len(prs2)} PRs in {time2:.2f} seconds")

        # Verify data is the same
        if prs1 == prs2:
            print(f"\n✓ Cache working! Second fetch was {time1/time2:.1f}x faster")
            return True
        else:
            print("\n✗ Cache data mismatch")
            return False

    except Exception as e:
        print(f"\n✗ Error testing cache: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    parser = argparse.ArgumentParser(description="Manual test for GitHub/GitLab GraphQL client")
    parser.add_argument(
        "--platform",
        choices=["github", "gitlab"],
        required=True,
        help="Platform to test (github or gitlab)",
    )
    parser.add_argument("--start", required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", required=True, help="End date (YYYY-MM-DD)")
    parser.add_argument("--author", help="Filter by author (optional)")
    parser.add_argument(
        "--max-prs", type=int, default=5, help="Maximum PRs to display (default: 5)"
    )

    args = parser.parse_args()

    # Print header
    print("\n" + "=" * 80)
    print(f"  🧪 {args.platform.upper()} GraphQL Client Test")
    print("=" * 80)

    # Check environment variables
    print("\n📋 Environment Check:")
    print("─" * 80)

    # Check URL (new GIT_URL or legacy GITHUB_URL)
    git_url = os.getenv("GIT_URL") or os.getenv("GITHUB_URL")
    if git_url:
        print(f"✓ GIT_URL (or GITHUB_URL): {git_url}")
    else:
        print("✗ GIT_URL / GITHUB_URL: NOT SET")

    # Check repo owner (new GIT_REPO_OWNER or legacy GITHUB_REPO_OWNER)
    repo_owner = os.getenv("GIT_REPO_OWNER") or os.getenv("GITHUB_REPO_OWNER")
    if repo_owner:
        print(f"✓ GIT_REPO_OWNER (or GITHUB_REPO_OWNER): {repo_owner}")
    else:
        print("✗ GIT_REPO_OWNER / GITHUB_REPO_OWNER: NOT SET")

    # Check repo name (new GIT_REPO_NAME or legacy GITHUB_REPO_NAME)
    repo_name = os.getenv("GIT_REPO_NAME") or os.getenv("GITHUB_REPO_NAME")
    if repo_name:
        print(f"✓ GIT_REPO_NAME (or GITHUB_REPO_NAME): {repo_name}")
    else:
        print("✗ GIT_REPO_NAME / GITHUB_REPO_NAME: NOT SET")

    # Check tokens
    git_token = os.getenv("GIT_TOKEN")
    github_token = os.getenv("GITHUB_TOKEN")
    gitlab_token = os.getenv("GITLAB_TOKEN")

    # Show token status
    if git_token:
        display_value = git_token[:4] + "..." + git_token[-4:] if len(git_token) > 8 else "***"
        print(f"✓ GIT_TOKEN: {display_value}")
    else:
        print("✗ GIT_TOKEN: NOT SET")

    if github_token:
        display_value = (
            github_token[:4] + "..." + github_token[-4:] if len(github_token) > 8 else "***"
        )
        print(f"✓ GITHUB_TOKEN: {display_value}")
    else:
        print("✗ GITHUB_TOKEN: NOT SET")

    if gitlab_token:
        display_value = (
            gitlab_token[:4] + "..." + gitlab_token[-4:] if len(gitlab_token) > 8 else "***"
        )
        print(f"✓ GITLAB_TOKEN: {display_value}")
    else:
        print("✗ GITLAB_TOKEN: NOT SET")

    # Check SSL verification setting
    verify_ssl_env = os.getenv("GIT_VERIFY_SSL", "true")
    print(f"ℹ️  GIT_VERIFY_SSL: {verify_ssl_env}")
    if verify_ssl_env.lower() in ("false", "0", "no"):
        print("⚠️  SSL verification is DISABLED (for self-signed certificates)")

    # Validate required variables
    missing = []

    if not git_url:
        missing.append("GIT_URL (or GITHUB_URL)")

    if not repo_owner:
        missing.append("GIT_REPO_OWNER (or GITHUB_REPO_OWNER)")

    if not repo_name:
        missing.append("GIT_REPO_NAME (or GITHUB_REPO_NAME)")

    # Check platform-specific token requirement
    if args.platform == "gitlab":
        if not git_token and not gitlab_token and not github_token:
            print("\n❌ GitLab requires a token:")
            print("   - Recommended: GIT_TOKEN or GITLAB_TOKEN")
            print("   - Legacy: GITHUB_TOKEN")
            missing.append("GIT_TOKEN / GITLAB_TOKEN / GITHUB_TOKEN")
    else:  # github
        if not git_token and not github_token:
            print("\n❌ GitHub requires a token:")
            print("   - Recommended: GIT_TOKEN or GITHUB_TOKEN")
            missing.append("GIT_TOKEN / GITHUB_TOKEN")

    if missing:
        print(f"\n❌ Missing required variables for {args.platform}")
        print("\n🔧 Recommended setup (new GIT_* variables):")
        if args.platform == "gitlab":
            print("   export GIT_URL='https://gitlab.com'")
            print("   export GITLAB_TOKEN='glpat-...'  # or GIT_TOKEN")
            print("   export GIT_REPO_OWNER='gitlab-org'")
            print("   export GIT_REPO_NAME='gitlab'")
        else:
            print("   export GIT_URL='https://github.com'")
            print("   export GITHUB_TOKEN='ghp-...'  # or GIT_TOKEN")
            print("   export GIT_REPO_OWNER='your-org'")
            print("   export GIT_REPO_NAME='your-repo'")
        print("\n📚 Legacy setup (GITHUB_* variables) is still supported.")
        return 1

    # Verify platform matches URL
    url_lower = git_url.lower() if git_url else ""
    if args.platform == "gitlab" and "gitlab" not in url_lower:
        print(f"\n⚠️  Warning: Platform is 'gitlab' but URL is '{git_url}'")
        print("   Did you mean to set GIT_URL to a GitLab instance?")
    elif args.platform == "github" and "gitlab" in url_lower:
        print(f"\n⚠️  Warning: Platform is 'github' but URL is '{git_url}'")
        print("   Did you mean to set GIT_URL to 'https://github.com'?")

    # Initialize client
    try:
        # Client will automatically read GIT_VERIFY_SSL environment variable
        client = GitGraphQLClient()

        # Verify detected platform
        detected_platform = "gitlab" if client.is_gitlab else "github"
        if detected_platform != args.platform:
            print(f"\n⚠️  Warning: Requested {args.platform} but detected {detected_platform}")
            print(f"   This is based on GIT_URL (or GITHUB_URL): {git_url}")

    except Exception as e:
        print(f"\n❌ Failed to initialize client: {e}")
        import traceback

        traceback.print_exc()
        return 1

    # Run tests
    results = []

    try:
        results.append(("Connection", test_connection(client)))
        results.append(("GraphQL Query", test_graphql_query(client)))
        results.append(
            (
                "Fetch PRs/MRs",
                test_fetch_prs(client, args.start, args.end, args.author, args.max_prs),
            )
        )
        results.append(("Metrics Validation", test_pr_metrics(client, args.start, args.end)))
        results.append(("Cache", test_cache(client, args.start, args.end)))

    except Exception as e:
        print(f"\n❌ Test suite failed with exception: {e}")
        import traceback

        traceback.print_exc()
        return 1

    # Print summary
    print("\n" + "=" * 80)
    print("  📊 TEST SUMMARY")
    print("=" * 80)

    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")

    print("\n" + "=" * 80)

    # Return exit code
    all_passed = all(result[1] for result in results)
    if all_passed:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print("\n⚠️  Some tests failed. See output above for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
